"""Phase 15 capstone: the full flow from the brief's closing diagram, in
one test —

    SEARCH -> COLLECTION -> NORMALIZATION -> MATCHING -> GROUPING
    -> COMPARISON -> SPEC COMPARISON -> REVIEWS -> SENTIMENT
    -> PROS/CONS -> PRICE HISTORY -> PREDICTION -> RECOMMENDATION -> ALERT

run against the real Postgres database (rolled back after the test), mock
collectors, and the real embedding/sentiment models — nothing mocked at
the service layer.
"""
import pytest

from app.config import Settings
from app.database.models import Product
from app.schemas.alert import CreateAlertRequest
from app.services.alert_service import check_price_alerts, create_alert
from app.services.comparison_service import get_comparison
from app.services.prediction_service import predict_listing_price
from app.services.price_service import get_product_price_history
from app.services.product_service import get_product
from app.services.recommendation_service import get_recommendations
from app.services.review_service import ensure_reviews_collected, get_review_summary
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


async def test_full_flow_search_to_alert(db_session):
    settings = Settings(mock_mode=True)

    # 1-6: SEARCH -> COLLECTION -> NORMALIZATION -> MATCHING -> GROUPING
    search_result = await run_search(db_session, "Apple iPhone 15", settings=settings)
    assert search_result.retailers_searched == ["amazon", "flipkart"]
    assert search_result.groups
    group = next(g for g in search_result.groups if g.retailer_count == 2)
    product_id = group.product_id

    # 7: COMMON PRODUCT GROUP — same product, genuinely different titles.
    product_out = get_product(db_session, product_id)
    titles = {l.product_name for l in product_out.listings}
    assert len(titles) == 2  # never byte-identical across retailers
    retailers = {l.retailer for l in product_out.listings}
    assert retailers == {"amazon", "flipkart"}

    # 8-9: PRICE COMPARISON + SPECIFICATION COMPARISON
    comparison = get_comparison(db_session, product_id)
    assert comparison.best_price_retailer in retailers
    assert comparison.specifications  # merged spec sheet, not empty

    # 10-12: REVIEW COLLECTION -> AI SENTIMENT -> PROS/CONS
    product = db_session.get(Product, product_id)
    await ensure_reviews_collected(db_session, product, settings=settings)
    db_session.refresh(product)
    review_summary = get_review_summary(db_session, product)
    assert review_summary.total_reviews_analyzed > 0
    assert review_summary.positive_percent is not None

    # 13-14: PRICE HISTORY -> PREDICTION
    history = get_product_price_history(db_session, product)
    assert history.current is not None
    prediction = predict_listing_price(db_session, product.listings[0])
    assert prediction.trend in ("UP", "DOWN", "STABLE", "INSUFFICIENT_DATA")

    # 15: PERSONALIZED RECOMMENDATION
    recommendations = get_recommendations(db_session, product)
    assert recommendations.product_id == product_id

    # 16: PRICE DROP ALERT
    target_listing = product.listings[0]
    alert = create_alert(
        db_session,
        CreateAlertRequest(
            listing_id=target_listing.id,
            email="e2e-test@example.com",
            target_price=(target_listing.current_price or 0) + 1,
        ),
    )
    db_session.flush()
    assert alert is not None

    triggered = check_price_alerts(db_session)
    assert triggered >= 1  # target was set above current price, so it fires
