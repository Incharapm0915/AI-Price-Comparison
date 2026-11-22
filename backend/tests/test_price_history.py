"""Phase 10 tests: price history aggregation, run against the real
Postgres database (rolled back after each test)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.database.models import Availability, PriceHistory
from app.services.price_service import get_product_price_history
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True)


async def test_price_history_single_collection_point(db_session, mock_settings):
    result = await run_search(db_session, "Dell XPS 13", settings=mock_settings)
    group = result.groups[0]

    from app.database.models import Product

    product = db_session.get(Product, group.product_id)
    history = get_product_price_history(db_session, product)

    assert history.highest is not None
    assert history.lowest is not None
    assert history.highest >= history.lowest
    assert history.current is not None
    assert history.average is not None
    assert len(history.points) == len(product.listings)  # one point per listing so far


async def test_price_history_aggregates_highest_lowest_average_over_time(db_session, mock_settings):
    """Directly seeds a multi-day price history (bypassing the collector,
    which only gives one point per day-bucket) to verify the aggregation
    math against known values."""
    result = await run_search(db_session, "LG UQ7500", settings=mock_settings)
    group = result.groups[0]

    from app.database.models import Product

    product = db_session.get(Product, group.product_id)
    listing = product.listings[0]

    # The search above already inserted one real PriceHistory point at
    # whatever price the mock collector generated — seed values relative to
    # it (not hardcoded absolutes) so this test doesn't depend on knowing
    # the collector's internal pricing.
    baseline = listing.current_price
    highest_seed = baseline * 2.0
    lowest_seed = baseline * 0.5

    now = datetime.now(timezone.utc)
    seeded_prices = [highest_seed, baseline * 1.5, lowest_seed, baseline * 1.1]
    for i, price in enumerate(seeded_prices):
        db_session.add(
            PriceHistory(
                listing_id=listing.id,
                price=price,
                mrp=price * 1.1,
                discount=9.0,
                currency="INR",
                availability=Availability.IN_STOCK,
                collected_at=now - timedelta(days=(len(seeded_prices) - i)),
            )
        )
    db_session.flush()

    history = get_product_price_history(db_session, product)
    assert history.highest == highest_seed
    assert history.lowest == lowest_seed
    assert history.lowest <= history.average <= history.highest


async def test_price_history_returns_empty_for_product_with_no_history(db_session):
    from app.database.models import Product

    product = Product(common_product_id="TEST_NO_HISTORY", canonical_name="Test Product")
    db_session.add(product)
    db_session.flush()

    history = get_product_price_history(db_session, product)
    assert history.highest is None
    assert history.lowest is None
    assert history.current is None
    assert history.points == []


def test_price_history_endpoint_404_for_unknown_product():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/api/products/does-not-exist/price-history")
    assert response.status_code == 404
