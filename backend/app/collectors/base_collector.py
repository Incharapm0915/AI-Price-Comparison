"""BaseCollector — the interface every retailer collector (mock or live)
implements. No retailer-specific scraping logic belongs anywhere outside
`app/collectors/`; API routes and services only ever talk to this interface.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from app.collectors.types import CollectedProduct, CollectedReview, CollectedListingSummary
from app.config import Settings, get_settings
from app.utils.logging import get_logger
from app.utils.validators import is_non_empty, is_valid_price, is_valid_url

logger = get_logger(__name__)


class BaseCollector(ABC):
    """Common contract + shared throttling/validation for all collectors.

    Concrete collectors implement `search_products`, `get_product`, and
    `get_reviews`. Browser-driven collectors (Phase 6/7) additionally
    implement `parse_product`/`parse_reviews` against a Playwright `Page`;
    mock collectors (Phase 3) generate data directly and don't need them.
    """

    retailer: str = "generic"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._last_request_at: float = 0.0

    # ── Public interface ─────────────────────────────────────────────
    @abstractmethod
    async def search_products(self, query: str, max_results: int | None = None) -> list[CollectedListingSummary]:
        """Search this retailer and return up to `max_results` candidate
        listings. Must raise `CollectorAccessDeniedError` (not retry forever)
        if automated access is denied."""

    @abstractmethod
    async def get_product(self, url: str) -> CollectedProduct:
        """Fetch and parse full product detail for a single listing URL."""

    @abstractmethod
    async def get_reviews(self, url: str, max_reviews: int | None = None) -> list[CollectedReview]:
        """Fetch up to `max_reviews` reviews for a listing, newest first
        where the retailer supports ordering. Returns [] if the retailer
        doesn't expose review text rather than fabricating any."""

    # ── Hooks for browser-driven collectors (Phase 6/7) ─────────────────
    def parse_product(self, page: Any) -> CollectedProduct:
        raise NotImplementedError(
            f"{type(self).__name__} does not parse live pages — "
            "browser-based parsing arrives in Phase 6/7."
        )

    def parse_reviews(self, page: Any) -> list[CollectedReview]:
        raise NotImplementedError(
            f"{type(self).__name__} does not parse live pages — "
            "browser-based parsing arrives in Phase 6/7."
        )

    # ── Shared normalization/validation ─────────────────────────────────
    def normalize_product(self, data: CollectedProduct) -> CollectedProduct:
        """Light collector-level cleanup (whitespace, empty-string -> None).
        The full normalization pipeline (brand/spec extraction, unit
        canonicalization) lives in `app.matching.normalizer` (Phase 4) and
        runs downstream of this in the service layer."""
        data.product_name = data.product_name.strip()
        if data.description:
            data.description = data.description.strip() or None
        data.image_urls = [u for u in data.image_urls if is_valid_url(u)]
        return data

    def validate_product(self, data: CollectedProduct) -> bool:
        """The minimum bar for a collected product to be usable at all."""
        if not is_non_empty(data.product_name):
            logger.warning("%s: rejected listing with empty product_name", self.retailer)
            return False
        if not is_valid_url(data.product_url):
            logger.warning("%s: rejected listing with invalid product_url", self.retailer)
            return False
        if not is_non_empty(data.retailer_product_id):
            logger.warning("%s: rejected listing with empty retailer_product_id", self.retailer)
            return False
        if data.price is not None and not is_valid_price(data.price):
            logger.warning("%s: rejected listing with invalid price %r", self.retailer, data.price)
            return False
        return True

    # ── Throttling (used by live/browser collectors; mock collectors don't
    # make real requests so they don't need to wait) ────────────────────
    async def _throttle(self) -> None:
        min_delay = self.settings.collector_min_delay_seconds
        elapsed = time.monotonic() - self._last_request_at
        remaining = min_delay - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request_at = time.monotonic()
