"""Celery tasks: update_price, check_price_alerts, plus a scheduled sweep
that refreshes listings nobody has re-collected in a while."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.database.connection import SessionLocal
from app.database.models import ProductListing
from app.services.alert_service import check_price_alerts
from app.services.search_service import refresh_listing
from app.utils.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.price_tasks.update_price_task", bind=True, max_retries=2)
def update_price_task(self, listing_id: str) -> dict:
    db = SessionLocal()
    try:
        listing = db.get(ProductListing, listing_id)
        if listing is None:
            return {"listing_id": listing_id, "status": "not_found"}
        ok = asyncio.run(refresh_listing(db, listing))
        db.commit()
        return {"listing_id": listing_id, "status": "updated" if ok else "failed"}
    finally:
        db.close()


@celery_app.task(name="app.workers.price_tasks.check_price_alerts_task")
def check_price_alerts_task() -> dict:
    db = SessionLocal()
    try:
        triggered = check_price_alerts(db)
        db.commit()
        logger.info("check_price_alerts_task: %d alert(s) triggered", triggered)
        return {"triggered": triggered}
    finally:
        db.close()


@celery_app.task(name="app.workers.price_tasks.refresh_stale_listings_task")
def refresh_stale_listings_task(limit: int = 50) -> dict:
    """Refreshes listings not re-collected in `stale_listing_refresh_days`
    days — bounded by `limit` per run so a large catalog can't turn this
    into an aggressive collection burst."""
    settings = get_settings()
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.stale_listing_refresh_days)
        stale = (
            db.query(ProductListing)
            .filter(ProductListing.collected_at < cutoff)
            .order_by(ProductListing.collected_at)
            .limit(limit)
            .all()
        )
        refreshed = 0
        for listing in stale:
            if asyncio.run(refresh_listing(db, listing)):
                refreshed += 1
        db.commit()
        logger.info("refresh_stale_listings_task: %d/%d refreshed", refreshed, len(stale))
        return {"checked": len(stale), "refreshed": refreshed}
    finally:
        db.close()
