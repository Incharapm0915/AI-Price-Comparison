"""Price-drop alerts. No account system exists in this project (see
PriceAlert's model docstring), so alerts are addressed by email directly."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import AlertStatus, PriceAlert, ProductListing
from app.schemas.alert import AlertOut, CreateAlertRequest
from app.utils.email import send_email
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_alert(db: Session, payload: CreateAlertRequest) -> AlertOut | None:
    listing = db.get(ProductListing, payload.listing_id)
    if listing is None:
        return None

    alert = PriceAlert(
        listing_id=payload.listing_id,
        email=payload.email,
        target_price=payload.target_price,
        status=AlertStatus.ACTIVE,
    )
    db.add(alert)
    db.flush()
    return _alert_out(alert, listing)


def list_alerts(db: Session, email: str) -> list[AlertOut]:
    alerts = (
        db.query(PriceAlert)
        .filter(PriceAlert.email == email, PriceAlert.status != AlertStatus.DELETED)
        .order_by(PriceAlert.created_at.desc())
        .all()
    )
    return [_alert_out(a, a.listing) for a in alerts]


def delete_alert(db: Session, alert_id: str) -> bool:
    alert = db.get(PriceAlert, alert_id)
    if alert is None:
        return False
    alert.status = AlertStatus.DELETED
    db.flush()
    return True


def check_price_alerts(db: Session) -> int:
    """Checks every ACTIVE alert against its listing's current price and
    triggers (marks TRIGGERED + sends an email) any that have hit target.
    Returns the number of alerts triggered. Safe to call repeatedly — a
    triggered alert won't fire twice."""
    active_alerts = db.query(PriceAlert).filter(PriceAlert.status == AlertStatus.ACTIVE).all()
    triggered_count = 0

    for alert in active_alerts:
        listing = alert.listing
        if listing is None or listing.current_price is None:
            continue
        if listing.current_price <= alert.target_price:
            _trigger_alert(alert, listing)
            triggered_count += 1

    db.flush()
    return triggered_count


def _trigger_alert(alert: PriceAlert, listing: ProductListing) -> None:
    from datetime import datetime, timezone

    alert.status = AlertStatus.TRIGGERED
    alert.triggered_at = datetime.now(timezone.utc)
    alert.triggered_price = listing.current_price

    send_email(
        to=alert.email,
        subject=f"Price drop: {listing.product_name}",
        body=(
            f"{listing.product_name} on {listing.retailer.title()} just dropped to "
            f"₹{listing.current_price:,.2f} — at or below your target of ₹{alert.target_price:,.2f}.\n\n"
            f"{listing.product_url}"
        ),
    )
    logger.info("Alert %s triggered for %s at %.2f (target %.2f)", alert.id, listing.retailer, listing.current_price, alert.target_price)


def _alert_out(alert: PriceAlert, listing: ProductListing) -> AlertOut:
    return AlertOut(
        id=alert.id,
        listing_id=alert.listing_id,
        retailer=listing.retailer,
        product_name=listing.product_name,
        email=alert.email,
        target_price=alert.target_price,
        current_price=listing.current_price,
        status=alert.status.value,
        triggered_at=alert.triggered_at,
        triggered_price=alert.triggered_price,
        created_at=alert.created_at,
    )
