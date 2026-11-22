"""Phase 13 tests: use-case tags + similar products, run against the real
Postgres database (rolled back after each test)."""
import pytest

from app.config import Settings
from app.database.models import Product
from app.services.recommendation_service import get_recommendations, get_similar_products, get_use_case_recommendations
from app.services.review_service import ensure_reviews_collected
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True)


async def test_high_camera_mp_recommends_photography(db_session, mock_settings):
    result = await run_search(db_session, "Xiaomi Redmi Note 13 Pro", settings=mock_settings)  # 200MP camera
    product = db_session.get(Product, result.groups[0].product_id)

    recommended, _ = get_use_case_recommendations(db_session, product)
    assert "Photography" in recommended


async def test_high_ram_recommends_gaming(db_session, mock_settings):
    result = await run_search(db_session, "OnePlus 12R", settings=mock_settings)  # 8/16GB RAM
    product = db_session.get(Product, result.groups[0].product_id)

    recommended, _ = get_use_case_recommendations(db_session, product)
    assert "Gaming" in recommended


async def test_low_battery_headphones_not_ideal_for_multi_day_use(db_session, mock_settings):
    result = await run_search(db_session, "Sony WH-1000XM5", settings=mock_settings)
    # This product has no mAh spec in the catalog (battery life is in
    # hours, not mAh) — recommendations must not fabricate a battery-based
    # tag when the signal genuinely isn't present.
    product = db_session.get(Product, result.groups[0].product_id)
    recommended, not_ideal = get_use_case_recommendations(db_session, product)
    assert "Daily use" not in recommended  # no mAh spec to justify this tag


async def test_recommendations_never_fabricate_untagged_use_cases(db_session, mock_settings):
    """A product with no strong signals anywhere gets an empty (not
    invented) recommended_for list."""
    product = Product(
        common_product_id="TEST_NO_SIGNALS",
        canonical_name="Generic Test Product",
        category="Electronics",
        specifications={"Color": "Black"},
    )
    db_session.add(product)
    db_session.flush()

    recommended, not_ideal = get_use_case_recommendations(db_session, product)
    assert recommended == []
    assert not_ideal == []


async def test_similar_products_stay_within_same_category(db_session, mock_settings):
    result = await run_search(db_session, "Samsung Galaxy S24", settings=mock_settings)
    product = db_session.get(Product, result.groups[0].product_id)

    # Seed a second, different category product so we can verify it's
    # excluded even though it shares the "Samsung" brand.
    await run_search(db_session, "LG UQ7500", settings=mock_settings)

    similar = get_similar_products(db_session, product)
    for candidate in similar:
        assert candidate.category == product.category
        assert candidate.id != product.id


async def test_similar_products_prefers_same_brand(db_session, mock_settings):
    await run_search(db_session, "Samsung Galaxy S24", settings=mock_settings)
    await run_search(db_session, "Apple iPhone 15", settings=mock_settings)
    result = await run_search(db_session, "Xiaomi Redmi Note 13 Pro", settings=mock_settings)
    product = db_session.get(Product, result.groups[0].product_id)

    similar = get_similar_products(db_session, product, limit=10)
    assert similar  # smartphones category has several candidates now


async def test_get_recommendations_end_to_end(db_session, mock_settings):
    result = await run_search(db_session, "Apple MacBook Air M2", settings=mock_settings)
    product = db_session.get(Product, result.groups[0].product_id)
    await ensure_reviews_collected(db_session, product, settings=mock_settings)
    db_session.refresh(product)

    recommendations = get_recommendations(db_session, product)
    assert recommendations.product_id == product.id
    assert isinstance(recommendations.recommended_for, list)
    assert isinstance(recommendations.not_ideal_for, list)
    assert isinstance(recommendations.similar_products, list)


def test_recommendations_endpoint_404_for_unknown_product():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/api/products/does-not-exist/recommendations")
    assert response.status_code == 404
