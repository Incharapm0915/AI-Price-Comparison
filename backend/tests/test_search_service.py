"""Phase 8 integration tests: collect (mock) -> match -> persist -> query,
run against the real Postgres database (rolled back after each test)."""
import pytest

from app.collectors.types import CollectorAccessDeniedError
from app.config import Settings
from app.database.models import PriceHistory, ProductListing
from app.services.comparison_service import get_comparison
from app.services.product_service import get_product
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True, collector_max_results_per_retailer=5)


async def test_search_matches_same_product_across_retailers(db_session, mock_settings):
    result = await run_search(db_session, "Samsung Galaxy S24", settings=mock_settings)

    assert result.retailers_searched == ["amazon", "flipkart"]
    assert result.retailers_failed == []
    assert result.groups

    multi_retailer_groups = [g for g in result.groups if g.retailer_count == 2]
    assert multi_retailer_groups, "expected at least one Samsung Galaxy S24 variant matched across both retailers"

    group = multi_retailer_groups[0]
    assert group.best_price is not None
    assert group.best_price_retailer in ("amazon", "flipkart")
    retailers_in_group = {l.retailer for l in group.listings}
    assert retailers_in_group == {"amazon", "flipkart"}


async def test_search_keeps_different_variants_as_separate_groups(db_session, mock_settings):
    result = await run_search(db_session, "iPhone 15", settings=mock_settings)
    assert len(result.groups) >= 2  # at least 128GB and 256GB variants

    # No group should mix two different storage capacities under one product.
    for group in result.groups:
        storages = {
            listing.specifications.get("Storage") for listing in group.listings if listing.specifications.get("Storage")
        }
        assert len(storages) <= 1, f"group {group.canonical_name!r} mixed storage variants: {storages}"


async def test_search_persists_price_history(db_session, mock_settings):
    await run_search(db_session, "OnePlus 12R", settings=mock_settings)

    listing_count = db_session.query(ProductListing).count()
    price_history_count = db_session.query(PriceHistory).count()
    assert listing_count > 0
    assert price_history_count >= listing_count  # at least one price point per listing


async def test_product_and_comparison_endpoints_reflect_search_results(db_session, mock_settings):
    result = await run_search(db_session, "Sony WH-1000XM5", settings=mock_settings)
    group = next(g for g in result.groups if g.retailer_count == 2)

    product = get_product(db_session, group.product_id)
    assert product is not None
    assert product.brand == "Sony"
    assert len(product.listings) == 2

    comparison = get_comparison(db_session, group.product_id)
    assert comparison is not None
    assert comparison.best_price_retailer in ("amazon", "flipkart")
    assert comparison.savings_vs_highest is not None
    assert comparison.savings_vs_highest >= 0


async def test_get_product_returns_none_for_unknown_id(db_session):
    assert get_product(db_session, "does-not-exist") is None


async def test_search_survives_one_retailer_being_blocked(db_session, mock_settings, monkeypatch):
    from app.collectors.mock_collector import MockFlipkartCollector

    async def deny(self, query, max_results=None):
        raise CollectorAccessDeniedError("flipkart: simulated block for this test")

    monkeypatch.setattr(MockFlipkartCollector, "search_products", deny)

    result = await run_search(db_session, "Apple iPhone 15", settings=mock_settings)
    assert result.retailers_searched == ["amazon"]
    assert result.retailers_failed == ["flipkart"]
    assert result.groups  # Amazon's results still came through
    assert all(g.retailer_count == 1 for g in result.groups)


async def test_search_with_no_matches_returns_empty_groups(db_session, mock_settings):
    result = await run_search(db_session, "completely nonexistent gadget xyz123", settings=mock_settings)
    assert result.groups == []
    assert result.retailers_searched == ["amazon", "flipkart"]
