"""CollectorFactory — the single place that decides mock vs. live and which
concrete collector class backs a given retailer name.

    collector = CollectorFactory.get("amazon")

Nothing outside this module should import a concrete collector class
directly — that's what keeps retailer-specific logic out of API routes and
services (per the brief's architecture rule).
"""
from __future__ import annotations

from app.collectors.amazon_collector import AmazonCollector
from app.collectors.base_collector import BaseCollector
from app.collectors.flipkart_collector import FlipkartCollector
from app.collectors.generic_collector import GenericRetailerCollector
from app.collectors.mock_collector import MockAmazonCollector, MockFlipkartCollector
from app.config import Settings, get_settings

# Retailers with a dedicated (non-generic) collector implementation.
SUPPORTED_RETAILERS: tuple[str, ...] = ("amazon", "flipkart")

_LIVE_COLLECTORS: dict[str, type[BaseCollector]] = {
    "amazon": AmazonCollector,
    "flipkart": FlipkartCollector,
}
_MOCK_COLLECTORS: dict[str, type[BaseCollector]] = {
    "amazon": MockAmazonCollector,
    "flipkart": MockFlipkartCollector,
}


class CollectorFactory:
    @staticmethod
    def get(retailer: str, settings: Settings | None = None) -> BaseCollector:
        settings = settings or get_settings()
        retailer = retailer.lower()

        if settings.mock_mode:
            collector_cls = _MOCK_COLLECTORS.get(retailer)
            if collector_cls is None:
                # Any retailer not yet in the mock catalog still gets a
                # working (empty-result) generic mock so callers don't have
                # to special-case unknown retailers.
                return GenericRetailerCollector(retailer, settings=settings)
            return collector_cls(settings)

        collector_cls = _LIVE_COLLECTORS.get(retailer)
        if collector_cls is not None:
            return collector_cls(settings)
        return GenericRetailerCollector(retailer, settings=settings)

    @staticmethod
    def get_all(retailers: list[str] | None = None, settings: Settings | None = None) -> list[BaseCollector]:
        retailers = retailers or list(SUPPORTED_RETAILERS)
        return [CollectorFactory.get(r, settings) for r in retailers]
