"""Celery task logic, called directly (Celery tasks are plain callables —
this exercises the same code the worker runs without needing a live broker;
scripts/live_collector_smoke_test.py-style manual dispatch already proved
the broker wiring itself works, see Phase 12).

Each task opens its own DB session (SessionLocal) and internally calls
`asyncio.run(...)` itself (workers are sync processes) — so these tests
must be plain sync functions, not `async def`, or Celery's own
`asyncio.run()` would collide with pytest-asyncio's event loop. Any async
setup needed (e.g. seeding data via `run_search`) uses `asyncio.run(...)`
directly, same as the task itself does.

Each task opens its own DB session (SessionLocal), so these tests point
SessionLocal at the same test database via monkeypatching rather than
using the `db_session` fixture directly — the tasks are meant to run
outside any request/test-fixture-scoped session.
"""
from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.slow


def _session_factory(db_session):
    """Celery tasks call SessionLocal() themselves and close() it when
    done; handing back the same already-open test session and no-op'ing
    close() keeps everything inside the test's rolled-back transaction."""

    class _NoCloseSession:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def close(self):
            pass  # the db_session fixture owns the real teardown

    return lambda: _NoCloseSession(db_session)


def test_collect_search_results_task_logic(db_session, monkeypatch):
    from app.workers import collection_tasks

    monkeypatch.setattr(collection_tasks, "SessionLocal", _session_factory(db_session))

    result = collection_tasks.collect_search_results_task.run("OnePlus 12R")
    assert result["query"] == "OnePlus 12R"
    assert result["groups"] > 0
    assert result["retailers_failed"] == []


def test_collect_product_task_refreshes_existing_listing(db_session, monkeypatch):
    from app.config import Settings
    from app.database.models import Product
    from app.services.search_service import run_search
    from app.workers import collection_tasks

    monkeypatch.setattr(collection_tasks, "SessionLocal", _session_factory(db_session))

    search_result = asyncio.run(run_search(db_session, "boAt Rockerz 550", settings=Settings(mock_mode=True)))
    product = db_session.get(Product, search_result.groups[0].product_id)
    listing_id = product.listings[0].id

    result = collection_tasks.collect_product_task.run(listing_id)
    assert result["status"] == "refreshed"


def test_collect_product_task_reports_not_found(db_session, monkeypatch):
    from app.workers import collection_tasks

    monkeypatch.setattr(collection_tasks, "SessionLocal", _session_factory(db_session))

    result = collection_tasks.collect_product_task.run("does-not-exist")
    assert result["status"] == "not_found"


def test_collect_reviews_task_collects_reviews(db_session, monkeypatch):
    from app.config import Settings
    from app.database.models import Product
    from app.services.search_service import run_search
    from app.workers import collection_tasks

    monkeypatch.setattr(collection_tasks, "SessionLocal", _session_factory(db_session))

    search_result = asyncio.run(run_search(db_session, "Apple Watch Series 9", settings=Settings(mock_mode=True)))
    product = db_session.get(Product, search_result.groups[0].product_id)
    listing_id = product.listings[0].id

    result = collection_tasks.collect_reviews_task.run(listing_id)
    assert result["reviews_collected"] > 0


def test_run_product_matching_task_updates_scores(db_session, monkeypatch):
    from app.config import Settings
    from app.services.search_service import run_search
    from app.workers import collection_tasks

    monkeypatch.setattr(collection_tasks, "SessionLocal", _session_factory(db_session))

    search_result = asyncio.run(run_search(db_session, "Samsung Galaxy S24", settings=Settings(mock_mode=True)))
    group = next(g for g in search_result.groups if g.retailer_count == 2)

    result = collection_tasks.run_product_matching_task.run(group.product_id)
    assert result["listings_updated"] == 2


def test_update_price_task(db_session, monkeypatch):
    from app.config import Settings
    from app.database.models import Product
    from app.services.search_service import run_search
    from app.workers import price_tasks

    monkeypatch.setattr(price_tasks, "SessionLocal", _session_factory(db_session))

    search_result = asyncio.run(run_search(db_session, "LG UQ7500", settings=Settings(mock_mode=True)))
    product = db_session.get(Product, search_result.groups[0].product_id)
    listing_id = product.listings[0].id

    result = price_tasks.update_price_task.run(listing_id)
    assert result["status"] == "updated"


def test_check_price_alerts_task_triggers(db_session, monkeypatch):
    from app.config import Settings
    from app.database.models import Product
    from app.schemas.alert import CreateAlertRequest
    from app.services.alert_service import create_alert
    from app.services.search_service import run_search
    from app.workers import price_tasks

    monkeypatch.setattr(price_tasks, "SessionLocal", _session_factory(db_session))

    search_result = asyncio.run(run_search(db_session, "Xiaomi Redmi Note 13 Pro", settings=Settings(mock_mode=True)))
    product = db_session.get(Product, search_result.groups[0].product_id)
    listing = product.listings[0]

    create_alert(
        db_session,
        CreateAlertRequest(listing_id=listing.id, email="task-test@example.com", target_price=listing.current_price + 1),
    )
    db_session.flush()

    result = price_tasks.check_price_alerts_task.run()
    assert result["triggered"] >= 1


def test_refresh_stale_listings_task_refreshes_nothing_when_all_fresh(db_session, monkeypatch):
    from app.config import Settings
    from app.services.search_service import run_search
    from app.workers import price_tasks

    monkeypatch.setattr(price_tasks, "SessionLocal", _session_factory(db_session))

    asyncio.run(run_search(db_session, "Dell XPS 13", settings=Settings(mock_mode=True)))

    result = price_tasks.refresh_stale_listings_task.run()
    assert result["checked"] == 0  # everything was just collected, nothing stale yet
