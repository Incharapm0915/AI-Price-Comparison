"""Shared pytest fixtures.

Tests that touch the database run against the real PostgreSQL instance
(DATABASE_URL) inside a transaction that's always rolled back — this
project has no SQLite fallback, per the spec ("PostgreSQL is the single
source of truth").
"""
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.database.connection import engine
from app.utils import robots as robots_module
from tests.fixtures.local_site_server import LocalSiteServer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def db_session():
    """A session bound to an outer transaction that's always rolled back —
    even if the code under test calls `session.commit()` (service-layer
    code does). `join_transaction_mode="create_savepoint"` makes commits
    release/reopen a SAVEPOINT instead of ending the outer transaction, so
    test isolation holds either way."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="session")
def local_site():
    server = LocalSiteServer(
        fixtures_dir=FIXTURES_DIR / "playwright_site",
        routes={
            "/search": "search_results.html",
            "/product/normal": "product_detail.html",
            "/product/blocked": "blocked.html",
            "/product/broken": "broken.html",
        },
        status_routes={"/product/forbidden": 403},
    )
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def amazon_site():
    server = LocalSiteServer(
        fixtures_dir=FIXTURES_DIR / "amazon_site",
        routes={
            "/s": "search_results.html",
            "/dp/B0TESTASIN1": "product_detail.html",
            "/product-reviews/B0TESTASIN1": "reviews.html",
        },
    )
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def flipkart_site():
    server = LocalSiteServer(
        fixtures_dir=FIXTURES_DIR / "flipkart_site",
        routes={
            "/search": "search_results.html",
            "/product/testpid": "product_detail.html",
        },
    )
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def clean_robots_cache(local_site):
    """robots.txt is cached per-origin; since each test may reconfigure the
    same local server's disallow rules, clear the cache before/after so
    tests don't see stale results from a previous test."""
    robots_module.clear_cache()
    local_site.set_disallow_paths([])
    yield
    robots_module.clear_cache()
    local_site.set_disallow_paths([])
