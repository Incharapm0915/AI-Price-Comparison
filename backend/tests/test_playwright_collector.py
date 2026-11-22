"""Phase 6 tests: the PlaywrightCollector framework, exercised against a
local test HTTP server (never a live retailer) so navigation, waits,
robots.txt enforcement, HTTP-status handling, retry/backoff, and CAPTCHA/
block detection are all verified against real Playwright + real HTTP
behavior."""
from __future__ import annotations

import pytest
from playwright.async_api import Page

from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.playwright_manager import PlaywrightManager
from app.collectors.types import (
    CollectedListingSummary,
    CollectedProduct,
    CollectedReview,
    CollectorAccessDeniedError,
    CollectorParseError,
)
from app.config import Settings

pytestmark = pytest.mark.slow


class _FixtureCollector(PlaywrightCollector):
    """A minimal concrete collector pointed at the local fixture site,
    standing in for what Phase 7's AmazonCollector/FlipkartCollector do
    against real markup."""

    retailer = "fixture"
    search_result_selector = ".result-card"
    product_detail_selector = "#product-title"
    navigation_timeout_ms = 3000

    def __init__(self, base_url: str, settings=None) -> None:
        super().__init__(settings)
        self.base_url = base_url

    def build_search_url(self, query: str) -> str:
        return f"{self.base_url}/search?q={query}"

    async def parse_search_results(self, page: Page) -> list[CollectedListingSummary]:
        cards = await page.locator(".result-card").all()
        results = []
        for card in cards:
            link = card.locator(".result-link")
            href = await link.get_attribute("href")
            title = await link.inner_text()
            price_text = await card.locator(".result-price").inner_text()
            rating_text = await card.locator(".result-rating").inner_text()
            results.append(
                CollectedListingSummary(
                    retailer=self.retailer,
                    retailer_product_id=href.rsplit("/", 1)[-1],
                    product_name=title,
                    product_url=f"{self.base_url}{href}",
                    price=float(price_text.replace("₹", "").replace(",", "")),
                    rating=float(rating_text),
                )
            )
        return results

    async def parse_product(self, page: Page) -> CollectedProduct:
        title = await page.locator("#product-title").inner_text()
        price_text = await page.locator("#product-price").inner_text()
        rating_text = await page.locator("#product-rating").inner_text()
        return CollectedProduct(
            retailer=self.retailer,
            retailer_product_id="normal",
            product_name=title,
            product_url=page.url,
            price=float(price_text.replace("₹", "").replace(",", "")),
            rating=float(rating_text),
        )

    async def parse_reviews(self, page: Page) -> list[CollectedReview]:
        cards = await page.locator(".review-card").all()
        reviews = []
        for card in cards:
            author = await card.locator(".review-author").inner_text()
            rating = await card.locator(".review-rating").inner_text()
            text = await card.locator(".review-text").inner_text()
            reviews.append(CollectedReview(reviewer_name=author, rating=float(rating), review_text=text))
        return reviews


@pytest.fixture()
def fixture_collector(local_site, clean_robots_cache):
    settings = Settings(collector_max_retries=1, collector_min_delay_seconds=0)
    return _FixtureCollector(local_site.base_url, settings=settings)


@pytest.fixture(autouse=True)
async def _reset_playwright_between_tests():
    """Each test function runs under its own event loop (pytest-asyncio's
    default), but PlaywrightManager's browser is bound to whichever loop
    created it — so it must be torn down at the end of every test, not
    shared across them, or the next test's loop can't use it."""
    yield
    await PlaywrightManager.shutdown()


async def test_search_products_extracts_listings(fixture_collector):
    results = await fixture_collector.search_products("test phone")
    assert len(results) == 2
    assert results[0].product_name == "Test Phone X 128GB Black"
    assert results[0].price == 49999.0
    assert results[0].rating == 4.5


async def test_get_product_extracts_detail(fixture_collector, local_site):
    product = await fixture_collector.get_product(f"{local_site.base_url}/product/normal")
    assert product.product_name == "Test Phone X 128GB Black"
    assert product.price == 49999.0


async def test_get_reviews_extracts_review_cards(fixture_collector, local_site):
    reviews = await fixture_collector.get_reviews(f"{local_site.base_url}/product/normal")
    assert len(reviews) == 2
    assert reviews[0].reviewer_name == "A. Tester"
    assert "camera" in reviews[0].review_text.lower()


async def test_block_page_raises_access_denied_not_retried(fixture_collector, local_site):
    with pytest.raises(CollectorAccessDeniedError):
        await fixture_collector.get_product(f"{local_site.base_url}/product/blocked")


async def test_http_403_raises_access_denied(fixture_collector, local_site):
    with pytest.raises(CollectorAccessDeniedError):
        await fixture_collector.get_product(f"{local_site.base_url}/product/forbidden")


async def test_missing_selector_raises_parse_error_after_retries(fixture_collector, local_site):
    with pytest.raises(CollectorParseError):
        await fixture_collector.get_product(f"{local_site.base_url}/product/broken")


async def test_robots_txt_disallow_blocks_collection_before_navigating(local_site, clean_robots_cache):
    local_site.set_disallow_paths(["/product/"])
    from app.utils import robots as robots_module

    robots_module.clear_cache()

    settings = Settings(collector_max_retries=0, collector_min_delay_seconds=0)
    collector = _FixtureCollector(local_site.base_url, settings=settings)
    with pytest.raises(CollectorAccessDeniedError):
        await collector.get_product(f"{local_site.base_url}/product/normal")


async def test_robots_txt_allows_when_not_disallowed(fixture_collector, local_site):
    # Baseline: with an empty disallow list (the default), collection works.
    product = await fixture_collector.get_product(f"{local_site.base_url}/product/normal")
    assert product.product_name
