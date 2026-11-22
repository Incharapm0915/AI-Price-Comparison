"""AmazonCollector parsing tests, run against a local fixture server (never
the live site) so they're deterministic and CI-safe. The fixture markup
mirrors the real amazon.in structure confirmed while building this adapter
(see scripts/live_collector_smoke_test.py for the live-verification step,
run manually/occasionally, not in CI)."""
import pytest

from app.collectors.amazon_collector import AmazonCollector
from app.collectors.playwright_manager import PlaywrightManager
from app.config import Settings

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
async def _reset_playwright_between_tests():
    yield
    await PlaywrightManager.shutdown()


@pytest.fixture()
def collector(amazon_site, clean_robots_cache):
    settings = Settings(mock_mode=False, collector_max_retries=0, collector_min_delay_seconds=0)
    c = AmazonCollector(settings)
    c.base_url = amazon_site.base_url
    return c


async def test_parse_search_results(collector):
    results = await collector.search_products("iPhone 15")
    assert len(results) == 2
    assert results[0].product_name == "Apple iPhone 15 (128 GB) - Black"
    assert results[0].price == 64999.0
    assert results[0].rating == 4.6
    assert results[0].retailer_product_id == "B0TESTASIN1"
    assert results[0].product_url.endswith("/dp/B0TESTASIN1")


async def test_parse_product_detail(collector, amazon_site):
    product = await collector.get_product(f"{amazon_site.base_url}/dp/B0TESTASIN1")
    assert product.product_name == "Apple iPhone 15 (128 GB) - Black"
    assert product.price == 64999.0
    assert product.mrp == 69900.0
    assert product.discount_percent == 7.0
    assert product.rating == 4.6
    assert product.rating_count == 12400
    assert product.availability == "IN_STOCK"
    assert product.specifications["Display"] == "6.1inch"  # unit-spacing normalized
    assert product.specifications["RAM"] == "6GB"
    assert "USB-C connector" in product.highlights
    assert len(product.image_urls) == 3  # main + 2 alt
    assert product.seller_name == "Appario Retail Pvt Ltd"
    assert product.identifiers["asin"] == "B0TESTASIN1"


async def test_parse_reviews(collector, amazon_site):
    reviews = await collector.get_reviews(f"{amazon_site.base_url}/dp/B0TESTASIN1")
    assert len(reviews) == 2

    first = reviews[0]
    assert first.reviewer_name == "A. Kumar"
    assert first.rating == 5.0
    assert first.review_title == "Excellent phone"
    assert "camera" in first.review_text.lower()
    assert first.verified_purchase is True
    assert first.helpful_count == 23

    second = reviews[1]
    assert second.verified_purchase is False  # no avp-badge present in fixture
