"""Phase 9 tests: sentiment analysis, aspect/pros-cons extraction, review
collection + summary, run against the real Postgres database (mock
collectors, rolled back after each test)."""
import pytest

from app.config import Settings
from app.database.models import Sentiment
from app.services.review_service import analyze_sentiment, ensure_reviews_collected, get_review_summary
from app.services.search_service import run_search

pytestmark = pytest.mark.slow


def test_analyze_sentiment_positive():
    sentiment, score = analyze_sentiment("The camera is amazing and battery life is excellent!")
    assert sentiment == Sentiment.POSITIVE
    assert score > 0


def test_analyze_sentiment_negative():
    sentiment, score = analyze_sentiment("Terrible battery life, very disappointed with this purchase.")
    assert sentiment == Sentiment.NEGATIVE
    assert score < 0


def test_analyze_sentiment_none_for_empty_text():
    assert analyze_sentiment(None) == (None, None)
    assert analyze_sentiment("   ") == (None, None)


@pytest.fixture()
def mock_settings() -> Settings:
    return Settings(mock_mode=True, max_reviews_per_product=15)


async def test_review_collection_and_summary_end_to_end(db_session, mock_settings):
    result = await run_search(db_session, "Sony WH-1000XM5", settings=mock_settings)
    group = next(g for g in result.groups if g.retailer_count == 2)

    from app.database.models import Product

    product = db_session.get(Product, group.product_id)
    await ensure_reviews_collected(db_session, product, settings=mock_settings)
    db_session.refresh(product)

    summary = get_review_summary(db_session, product)

    assert summary.total_reviews_analyzed > 0
    assert summary.positive_percent is not None
    total_pct = (summary.positive_percent or 0) + (summary.neutral_percent or 0) + (summary.negative_percent or 0)
    assert 99.0 <= total_pct <= 101.0  # rounding tolerance

    assert "amazon" in summary.retailer_ratings
    assert "flipkart" in summary.retailer_ratings
    assert summary.sample_reviews


async def test_ensure_reviews_collected_is_idempotent(db_session, mock_settings):
    from app.database.models import Product, Review

    result = await run_search(db_session, "boAt Rockerz 550", settings=mock_settings)
    group = result.groups[0]
    product = db_session.get(Product, group.product_id)

    await ensure_reviews_collected(db_session, product, settings=mock_settings)
    db_session.refresh(product)
    first_count = db_session.query(Review).filter(
        Review.listing_id.in_([l.id for l in product.listings])
    ).count()
    assert first_count > 0

    # Second call should not duplicate reviews (listings already have some).
    await ensure_reviews_collected(db_session, product, settings=mock_settings)
    second_count = db_session.query(Review).filter(
        Review.listing_id.in_([l.id for l in product.listings])
    ).count()
    assert second_count == first_count


def test_pros_cons_never_invent_unmentioned_aspects(db_session, mock_settings):
    """An aspect that's never mentioned in any review must never appear in
    pros/cons/most_mentioned_features — sanity-checked against a product
    with zero reviews collected."""
    from app.database.models import Product

    product = Product(common_product_id="TEST_EMPTY_REVIEWS", canonical_name="Test Product With No Reviews")
    db_session.add(product)
    db_session.flush()

    summary = get_review_summary(db_session, product)
    assert summary.total_reviews_analyzed == 0
    assert summary.pros == []
    assert summary.cons == []
    assert summary.most_mentioned_features == []
