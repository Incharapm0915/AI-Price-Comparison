"""Phase 12 tests: price-drop alerts, run against the real Postgres
database (rolled back after each test)."""
import pytest

from app.config import Settings
from app.database.models import AlertStatus, PriceAlert
from app.schemas.alert import CreateAlertRequest
from app.services.alert_service import check_price_alerts, create_alert, delete_alert, list_alerts
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True)


async def test_create_and_list_alert(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    listing = result.groups[0].listings[0]

    alert = create_alert(
        db_session, CreateAlertRequest(listing_id=listing.id, email="buyer@example.com", target_price=1000.0)
    )
    db_session.flush()
    assert alert is not None
    assert alert.status == "ACTIVE"

    alerts = list_alerts(db_session, "buyer@example.com")
    assert len(alerts) == 1
    assert alerts[0].id == alert.id


async def test_create_alert_returns_none_for_unknown_listing(db_session):
    result = create_alert(
        db_session, CreateAlertRequest(listing_id="does-not-exist", email="buyer@example.com", target_price=100.0)
    )
    assert result is None


async def test_check_price_alerts_triggers_when_price_at_or_below_target(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    listing = result.groups[0].listings[0]
    current_price = listing.price

    alert = create_alert(
        db_session,
        CreateAlertRequest(listing_id=listing.id, email="buyer@example.com", target_price=current_price + 1),
    )
    db_session.flush()

    triggered = check_price_alerts(db_session)
    assert triggered == 1

    db_alert = db_session.get(PriceAlert, alert.id)
    assert db_alert.status == AlertStatus.TRIGGERED
    assert db_alert.triggered_price == current_price
    assert db_alert.triggered_at is not None


async def test_check_price_alerts_does_not_trigger_above_target(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    listing = result.groups[0].listings[0]
    current_price = listing.price

    alert = create_alert(
        db_session,
        CreateAlertRequest(listing_id=listing.id, email="buyer@example.com", target_price=current_price - 500),
    )
    db_session.flush()

    triggered = check_price_alerts(db_session)
    assert triggered == 0

    db_alert = db_session.get(PriceAlert, alert.id)
    assert db_alert.status == AlertStatus.ACTIVE


async def test_check_price_alerts_never_fires_twice(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    listing = result.groups[0].listings[0]

    create_alert(
        db_session,
        CreateAlertRequest(listing_id=listing.id, email="buyer@example.com", target_price=listing.price + 1),
    )
    db_session.flush()

    first_pass = check_price_alerts(db_session)
    second_pass = check_price_alerts(db_session)
    assert first_pass == 1
    assert second_pass == 0  # already TRIGGERED, not ACTIVE anymore


async def test_delete_alert_soft_deletes(db_session, mock_settings):
    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    listing = result.groups[0].listings[0]

    alert = create_alert(
        db_session, CreateAlertRequest(listing_id=listing.id, email="buyer@example.com", target_price=1000.0)
    )
    db_session.flush()

    assert delete_alert(db_session, alert.id) is True
    assert list_alerts(db_session, "buyer@example.com") == []
    assert delete_alert(db_session, "does-not-exist") is False
