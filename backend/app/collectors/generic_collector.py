"""Generic retailer collector — for any additional retailer (Croma, Reliance
Digital, ...) added later behind the same `BaseCollector` interface, built
out in Phase 6/7. Parameterized by retailer name + a small site-config
(search URL pattern, CSS/locator selectors) instead of one hard-coded class
per retailer, since most sites only differ in markup, not in flow.
"""
from __future__ import annotations

from app.collectors.base_collector import BaseCollector
from app.collectors.types import CollectedListingSummary, CollectedProduct, CollectedReview


class GenericRetailerCollector(BaseCollector):
    def __init__(self, retailer: str, site_config: dict | None = None, settings=None) -> None:
        super().__init__(settings)
        self.retailer = retailer
        self.site_config = site_config or {}

    async def search_products(self, query: str, max_results: int | None = None) -> list[CollectedListingSummary]:
        raise NotImplementedError(
            f"Live collection for {self.retailer!r} arrives in Phase 6/7 (Playwright)."
        )

    async def get_product(self, url: str) -> CollectedProduct:
        raise NotImplementedError(
            f"Live collection for {self.retailer!r} arrives in Phase 6/7 (Playwright)."
        )

    async def get_reviews(self, url: str, max_reviews: int | None = None) -> list[CollectedReview]:
        raise NotImplementedError(
            f"Live collection for {self.retailer!r} arrives in Phase 6/7 (Playwright)."
        )
