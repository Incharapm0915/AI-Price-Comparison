"""FlipkartCollector parsing tests, run against a local fixture server
(never the live site) so they're deterministic and CI-safe. The fixture
markup mirrors the real flipkart.com structure confirmed while building
this adapter — including the product-detail page's hashed/atomic CSS
classes, reproduced here as literal class names since the collector
deliberately does NOT select on them (see the collector's docstring)."""
import pytest

from app.collectors.flipkart_collector import FlipkartCollector
from app.collectors.playwright_manager import PlaywrightManager
from app.config import Settings

pytestmark = pytest.mark.slow


@pytest.fixture(autouse=True)
async def _reset_playwright_between_tests():
    yield
    await PlaywrightManager.shutdown()


@pytest.fixture()
def collector(flipkart_site, clean_robots_cache):
    settings = Settings(mock_mode=False, collector_max_retries=0, collector_min_delay_seconds=0)
    c = FlipkartCollector(settings)
    c.base_url = flipkart_site.base_url
    return c


async def test_parse_search_results(collector):
    results = await collector.search_products("iPhone 15")
    assert len(results) == 2
    assert results[0].product_name == "Apple iPhone 15 (Black, 128 GB)"
    assert results[0].price == 63999.0
    assert results[0].rating == 4.6
    assert results[0].retailer_product_id == "testpid"
    assert "/product/testpid?pid=testpid" in results[0].product_url

    assert results[1].product_name == "Apple iPhone 15 (Black, 256 GB)"
    assert results[1].price == 73499.0


async def test_parse_product_detail_ignores_unrelated_carousel_price(collector, flipkart_site):
    """The fixture deliberately includes a "recommended product" price
    (₹9,999) rendered *before* the <h1> in document order — parse_product
    must land on the real buy-box price (₹63,999) after it, not that one."""
    product = await collector.get_product(f"{flipkart_site.base_url}/product/testpid?pid=testpid")
    assert product.product_name == "Apple iPhone 15 (Black, 128 GB)"
    assert product.price == 63999.0
    assert product.specifications["RAM"] == "6GB"
    assert product.specifications["Storage"] == "128GB"
    assert "128 GB ROM" in product.highlights
    assert len(product.image_urls) == 2
    assert product.identifiers["pid"] == "testpid"
