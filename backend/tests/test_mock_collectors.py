"""Phase 3 tests: mock collectors implement the BaseCollector contract and
return realistic, internally-consistent data with zero live retailer access."""
import pytest

from app.collectors.collector_factory import CollectorFactory
from app.collectors.mock_collector import MockAmazonCollector, MockFlipkartCollector
from app.config import Settings


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True)


def test_factory_returns_mock_collectors_when_mock_mode(mock_settings):
    amazon = CollectorFactory.get("amazon", mock_settings)
    flipkart = CollectorFactory.get("flipkart", mock_settings)
    assert isinstance(amazon, MockAmazonCollector)
    assert isinstance(flipkart, MockFlipkartCollector)


def test_factory_returns_live_collectors_when_not_mock_mode():
    settings = Settings(mock_mode=False)
    amazon = CollectorFactory.get("amazon", settings)
    from app.collectors.amazon_collector import AmazonCollector

    assert isinstance(amazon, AmazonCollector)


async def test_search_products_finds_relevant_results(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    results = await collector.search_products("iPhone 15")
    assert results
    assert all("iphone" in r.product_name.lower() or "apple" in r.product_name.lower() for r in results)


async def test_search_products_respects_max_results(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    results = await collector.search_products("smartphone", max_results=2)
    assert len(results) <= 2


async def test_search_products_no_match_returns_empty(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    results = await collector.search_products("nonexistent product xyz123")
    assert results == []


async def test_get_product_returns_full_detail(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    [summary] = (await collector.search_products("Galaxy S24", max_results=1))
    product = await collector.get_product(summary.product_url)

    assert product.brand == "Samsung"
    assert product.model == "Galaxy S24"
    assert product.price and product.price > 0
    assert product.rating_breakdown and sum(product.rating_breakdown.values()) > 0
    assert collector.validate_product(product) is True


async def test_amazon_and_flipkart_word_the_same_product_differently(mock_settings):
    """The exact scenario from the brief: same physical product, genuinely
    different titles across retailers."""
    amazon = MockAmazonCollector(mock_settings)
    flipkart = MockFlipkartCollector(mock_settings)

    amazon_results = await amazon.search_products("Samsung Galaxy S24")
    flipkart_results = await flipkart.search_products("Samsung Galaxy S24")

    assert amazon_results and flipkart_results
    amazon_titles = {r.product_name for r in amazon_results}
    flipkart_titles = {r.product_name for r in flipkart_results}
    assert amazon_titles.isdisjoint(flipkart_titles)  # never byte-for-byte identical
    # But both mention brand/model somewhere.
    assert any("Samsung" in t and "Galaxy S24" in t for t in amazon_titles)
    assert any("Samsung" in t and "Galaxy S24" in t for t in flipkart_titles)


async def test_retailer_exclusive_product_only_on_its_retailer(mock_settings):
    amazon = MockAmazonCollector(mock_settings)
    flipkart = MockFlipkartCollector(mock_settings)

    amazon_echo = await amazon.search_products("Echo Dot")
    flipkart_echo = await flipkart.search_products("Echo Dot")
    assert amazon_echo
    assert flipkart_echo == []

    # A brand-specific query, not generic terms like "smart"/"tv" that
    # legitimately match other retailers' unrelated products too.
    flipkart_marq = await flipkart.search_products("MarQ")
    amazon_marq = await amazon.search_products("MarQ")
    assert flipkart_marq
    assert amazon_marq == []


async def test_different_storage_variants_are_distinct_listings(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    results = await collector.search_products("iPhone 15", max_results=20)
    variants = {r.retailer_product_id for r in results}
    assert len(variants) >= 2  # at least two distinct storage/color combos


async def test_get_reviews_returns_bounded_realistic_reviews(mock_settings):
    collector = MockAmazonCollector(mock_settings)
    [summary] = (await collector.search_products("Sony WH-1000XM5", max_results=1))
    reviews = await collector.get_reviews(summary.product_url, max_reviews=10)

    assert reviews
    assert len(reviews) <= 10
    for r in reviews:
        assert 1.0 <= r.rating <= 5.0
        assert r.review_text
        assert r.reviewer_name


async def test_get_reviews_respects_max_reviews_per_product_setting():
    settings = Settings(mock_mode=True, max_reviews_per_product=3)
    collector = MockAmazonCollector(settings)
    [summary] = (await collector.search_products("boAt Rockerz", max_results=1))
    reviews = await collector.get_reviews(summary.product_url, max_reviews=50)
    assert len(reviews) <= 3


def test_validate_product_rejects_missing_fields(mock_settings):
    from app.collectors.types import CollectedProduct

    collector = MockAmazonCollector(mock_settings)
    bad = CollectedProduct(retailer="amazon", retailer_product_id="", product_name="", product_url="not-a-url")
    assert collector.validate_product(bad) is False
