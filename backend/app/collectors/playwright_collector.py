"""PlaywrightCollector — the shared browser-driven collection flow every
live retailer adapter (Phase 7) plugs into.

Handles once, here, so retailer adapters don't each reimplement it:
robots.txt enforcement, request throttling, locator-based explicit waits
(no fixed `sleep`s), retry with exponential backoff on transient failures,
and CAPTCHA/block-page detection that stops gracefully rather than
retrying into a wall or attempting to circumvent it.

A concrete adapter only implements:
    build_search_url(query)          -> str
    parse_search_results(page)       -> list[CollectedListingSummary]
    parse_product(page)              -> CollectedProduct
    parse_reviews(page)              -> list[CollectedReview]
and, optionally, `additional_block_indicators()` / `build_reviews_url()`.
"""
from __future__ import annotations

import asyncio
import random
from abc import abstractmethod
from typing import Awaitable, Callable, TypeVar

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.collectors.base_collector import BaseCollector
from app.collectors.playwright_manager import PlaywrightManager
from app.collectors.types import (
    CollectedListingSummary,
    CollectedProduct,
    CollectedReview,
    CollectorAccessDeniedError,
    CollectorParseError,
)
from app.utils.logging import get_logger
from app.utils.robots import is_allowed

logger = get_logger(__name__)

T = TypeVar("T")

# Generic phrases that show up on block/CAPTCHA interstitials across most
# retailers. Adapters can extend this via `additional_block_indicators()`
# with site-specific copy.
_BLOCK_INDICATORS = [
    "captcha", "are you a human", "unusual traffic", "access denied",
    "robot check", "verify you are a human", "automated access",
    "enter the characters you see", "pardon our interruption",
]

# A plain, honest desktop-browser user agent — not a spoofed/rotated one.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class PlaywrightCollector(BaseCollector):
    search_result_selector: str = "body"
    product_detail_selector: str = "body"
    # Reviews often live on a differently-structured page/tab than the
    # product detail page; falls back to product_detail_selector when a
    # collector doesn't need a distinct one (e.g. reviews embedded inline).
    reviews_wait_selector: str | None = None
    navigation_timeout_ms: int = 15000

    # ── hooks concrete adapters implement (Phase 7) ─────────────────────
    @abstractmethod
    def build_search_url(self, query: str) -> str: ...

    @abstractmethod
    async def parse_search_results(self, page: Page) -> list[CollectedListingSummary]: ...

    def build_reviews_url(self, product_url: str) -> str:
        """Default: reviews live on the product page itself. Adapters whose
        retailer uses a separate reviews URL/tab override this."""
        return product_url

    def additional_block_indicators(self) -> list[str]:
        return []

    # ── BaseCollector interface ─────────────────────────────────────────
    async def search_products(self, query: str, max_results: int | None = None) -> list[CollectedListingSummary]:
        limit = max_results or self.settings.collector_max_results_per_retailer
        url = self.build_search_url(query)
        results = await self._collect(url, self.search_result_selector, self.parse_search_results)
        return results[:limit]

    async def get_product(self, url: str) -> CollectedProduct:
        product = await self._collect(url, self.product_detail_selector, self.parse_product)
        return self.normalize_product(product)

    async def get_reviews(self, url: str, max_reviews: int | None = None) -> list[CollectedReview]:
        limit = max_reviews or self.settings.max_reviews_per_product
        reviews_url = self.build_reviews_url(url)
        wait_selector = self.reviews_wait_selector or self.product_detail_selector
        try:
            reviews = await self._collect(reviews_url, wait_selector, self.parse_reviews)
        except CollectorParseError:
            # A product genuinely having zero reviews (or a reviews-section
            # selector that never appears because there's nothing to show)
            # is a normal, common state — not a collection failure. A real
            # block/CAPTCHA still raises CollectorAccessDeniedError above,
            # which is not caught here.
            logger.info("%s: no reviews found/parseable at %s; returning empty list", self.retailer, reviews_url)
            return []
        return reviews[:limit]

    # ── shared machinery ─────────────────────────────────────────────
    async def _collect(
        self,
        url: str,
        wait_selector: str,
        parse_fn: Callable[[Page], Awaitable[T]],
    ) -> T:
        if not is_allowed(url):
            raise CollectorAccessDeniedError(f"{self.retailer}: robots.txt disallows {url}")

        await self._throttle()

        last_error: Exception | None = None
        max_attempts = self.settings.collector_max_retries + 1
        for attempt in range(max_attempts):
            try:
                return await self._load_and_parse(url, wait_selector, parse_fn)
            except CollectorAccessDeniedError:
                raise  # stop gracefully — never retry past a block/CAPTCHA
            except (PlaywrightTimeoutError, CollectorParseError) as exc:
                last_error = exc
                logger.warning(
                    "%s: attempt %d/%d failed for %s: %s",
                    self.retailer, attempt + 1, max_attempts, url, exc,
                )
                if attempt < max_attempts - 1:
                    backoff = (2 ** attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(backoff)

        raise CollectorParseError(f"{self.retailer}: giving up on {url} after {max_attempts} attempts") from last_error

    async def _load_and_parse(
        self,
        url: str,
        wait_selector: str,
        parse_fn: Callable[[Page], Awaitable[T]],
    ) -> T:
        async with PlaywrightManager.new_context(user_agent=_USER_AGENT) as context:
            page = await context.new_page()
            page.set_default_timeout(self.navigation_timeout_ms)

            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
            if response is not None and response.status in (403, 429, 503):
                raise CollectorAccessDeniedError(f"{self.retailer}: HTTP {response.status} for {url}")

            await self._check_for_block(page)

            try:
                await page.wait_for_selector(wait_selector, timeout=self.navigation_timeout_ms)
            except PlaywrightTimeoutError as exc:
                # A stalled wait can itself mean the real content never
                # arrived because a block page loaded instead — check.
                await self._check_for_block(page)
                raise CollectorParseError(
                    f"{self.retailer}: expected selector {wait_selector!r} never appeared on {url}"
                ) from exc

            result = await parse_fn(page)
            await page.close()
            return result

    async def _check_for_block(self, page: Page) -> None:
        try:
            content = (await page.content()).lower()
        except Exception:
            return
        for indicator in _BLOCK_INDICATORS + self.additional_block_indicators():
            if indicator in content:
                raise CollectorAccessDeniedError(f"{self.retailer}: block/CAPTCHA indicator {indicator!r} detected")
