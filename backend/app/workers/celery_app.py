"""Celery app + beat schedule. Run a worker + beat process alongside the
API (see docker-compose.yml / README):

    celery -A app.workers.celery_app worker --loglevel=info
    celery -A app.workers.celery_app beat --loglevel=info

Schedules are configurable via Settings (env vars), and deliberately
infrequent by default — this project's data collection policy explicitly
rules out aggressive/high-frequency collection.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "price_comparison",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.collection_tasks", "app.workers.price_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "check-price-alerts": {
        "task": "app.workers.price_tasks.check_price_alerts_task",
        "schedule": crontab(minute=f"*/{settings.price_alert_check_interval_minutes}"),
    },
    "refresh-stale-listing-prices": {
        "task": "app.workers.price_tasks.refresh_stale_listings_task",
        "schedule": crontab(minute=0, hour=f"*/{settings.price_refresh_interval_hours}"),
    },
}
