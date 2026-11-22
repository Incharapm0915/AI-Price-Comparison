"""Phase 11 tests: price prediction, run against the real Postgres
database (rolled back after each test)."""
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.database.models import Availability, PriceHistory, Product
from app.services.prediction_service import predict_listing_price
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True)


def _seed_price_series(db_session, listing_id: str, prices: list[float]) -> None:
    # Full control over the series: clear whatever the collector itself
    # already inserted during run_search (its timestamp/price would
    # otherwise land wherever it likes relative to these seeded points).
    db_session.query(PriceHistory).filter_by(listing_id=listing_id).delete()
    now = datetime.now(timezone.utc)
    for i, price in enumerate(prices):
        db_session.add(
            PriceHistory(
                listing_id=listing_id,
                price=price,
                mrp=price * 1.1,
                discount=9.0,
                currency="INR",
                availability=Availability.IN_STOCK,
                collected_at=now - timedelta(days=(len(prices) - i)),
            )
        )
    db_session.flush()


async def test_insufficient_data_below_minimum_points(db_session, mock_settings):
    result = await run_search(db_session, "Xiaomi Redmi Note 13 Pro", settings=mock_settings)
    group = result.groups[0]
    product = db_session.get(Product, group.product_id)
    listing = product.listings[0]  # exactly 1 point exists so far (below MIN_DATA_POINTS)

    prediction = predict_listing_price(db_session, listing)
    assert prediction.trend == "INSUFFICIENT_DATA"
    assert prediction.predicted_price is None
    assert prediction.confidence is None


async def test_predicts_downward_trend_from_declining_prices(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    group = result.groups[0]
    product = db_session.get(Product, group.product_id)
    listing = product.listings[0]

    _seed_price_series(db_session, listing.id, [2200.0, 2150.0, 2100.0, 2050.0, 2000.0, 1950.0])

    prediction = predict_listing_price(db_session, listing)
    assert prediction.trend == "DOWN"
    assert prediction.predicted_price is not None
    assert prediction.predicted_price < prediction.current_price
    assert prediction.predicted_range_low <= prediction.predicted_price <= prediction.predicted_range_high
    assert 0.0 <= prediction.confidence <= 1.0


async def test_predicts_upward_trend_from_rising_prices(db_session, mock_settings):
    result = await run_search(db_session, "Apple Watch Series 9", settings=mock_settings)
    group = result.groups[0]
    product = db_session.get(Product, group.product_id)
    listing = product.listings[0]

    # ~2.3%/day rise, matching the DOWN test's relative slope — needs to
    # clearly cross the classifier's threshold, not just trend upward.
    _seed_price_series(db_session, listing.id, [40000.0, 41000.0, 42000.0, 43000.0, 44000.0, 45000.0])

    prediction = predict_listing_price(db_session, listing)
    assert prediction.trend == "UP"
    assert prediction.predicted_price > prediction.current_price


async def test_predicts_stable_trend_from_flat_prices(db_session, mock_settings):
    result = await run_search(db_session, "Dell XPS 13", settings=mock_settings)
    group = result.groups[0]
    product = db_session.get(Product, group.product_id)
    listing = product.listings[0]

    _seed_price_series(db_session, listing.id, [89990.0, 89990.0, 89990.0, 89990.0, 89990.0, 89990.0])

    prediction = predict_listing_price(db_session, listing)
    assert prediction.trend == "STABLE"


def test_prediction_endpoint_404_for_unknown_product():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/api/products/does-not-exist/price-prediction")
    assert response.status_code == 404
