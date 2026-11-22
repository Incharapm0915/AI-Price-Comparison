"""Review collection + AI sentiment analysis / pros-cons summarization.

Sentiment: VADER (lexicon-based, no heavyweight model to load — reviews
are typically short, informal text VADER handles well) classifies each
review independently as POSITIVE/NEUTRAL/NEGATIVE with a compound score.

Pros/cons: a fixed aspect-keyword table maps review text to product
aspects (Camera, Battery, Display, ...); an aspect becomes a "pro" when
its positive mentions outweigh negative ones (and vice versa for "cons").
Never fabricates a pro/con for an aspect nobody actually mentioned.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.collectors.collector_factory import CollectorFactory
from app.collectors.types import CollectorError
from app.config import Settings, get_settings
from app.database.models import Product, ProductListing, Review, Sentiment
from app.schemas.review import ReviewOut, ReviewSummaryOut
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Sentiment ────────────────────────────────────────────────────────────
_analyzer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def analyze_sentiment(text: str | None) -> tuple[Sentiment | None, float | None]:
    """Returns (None, None) for missing/empty text — sentiment is never
    guessed for a review with no text."""
    if not text or not text.strip():
        return None, None
    compound = _get_analyzer().polarity_scores(text)["compound"]
    if compound >= 0.05:
        sentiment = Sentiment.POSITIVE
    elif compound <= -0.05:
        sentiment = Sentiment.NEGATIVE
    else:
        sentiment = Sentiment.NEUTRAL
    return sentiment, round(compound, 4)


# ── Aspect extraction ────────────────────────────────────────────────────
ASPECT_KEYWORDS: dict[str, list[str]] = {
    "Camera": ["camera", "photo", "picture", "selfie"],
    "Battery": ["battery", "charging", "charge", "backup"],
    "Display": ["display", "screen", "resolution", "brightness"],
    "Performance": ["performance", "speed", "lag", "smooth", "processor", "stutter"],
    "Build Quality": ["build quality", "design", "sturdy", "premium", "plastic", "durable"],
    "Software": ["software", "update", "bug", "ui", "interface"],
    "Price": ["price", "expensive", "value for money", "worth", "cheap", "overpriced"],
    "Sound": ["sound", "audio", "speaker", "bass"],
    "Comfort": ["comfort", "comfortable", "cushion"],
    "Customer Support": ["customer support", "support", "service"],
}


def _extract_aspects(text: str) -> set[str]:
    lower = text.lower()
    return {aspect for aspect, keywords in ASPECT_KEYWORDS.items() if any(k in lower for k in keywords)}


# ── Collection ───────────────────────────────────────────────────────────
async def collect_reviews_for_listing(db: Session, listing: ProductListing, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    collector = CollectorFactory.get(listing.retailer, settings)
    try:
        collected = await collector.get_reviews(listing.product_url, settings.max_reviews_per_product)
    except CollectorError as exc:
        logger.warning("%s: review collection failed for listing %s: %s", listing.retailer, listing.id, exc)
        return 0

    count = 0
    for item in collected:
        existing = None
        if item.external_review_id:
            existing = (
                db.query(Review)
                .filter_by(listing_id=listing.id, external_review_id=item.external_review_id)
                .one_or_none()
            )
        review = existing or Review(listing_id=listing.id, external_review_id=item.external_review_id)
        review.reviewer_name = item.reviewer_name
        review.rating = item.rating
        review.review_title = item.review_title
        review.review_text = item.review_text
        review.review_date = item.review_date
        review.verified_purchase = item.verified_purchase
        review.helpful_count = item.helpful_count
        review.review_images = item.review_images

        review.sentiment, review.sentiment_score = analyze_sentiment(item.review_text)

        if existing is None:
            db.add(review)
        count += 1

    db.flush()
    return count


async def ensure_reviews_collected(db: Session, product: Product, settings: Settings | None = None) -> None:
    """Collects reviews for any listing of this product that doesn't have
    any yet — cheap no-op on repeat calls once reviews exist."""
    collected_any = False
    for listing in product.listings:
        has_reviews = db.query(Review.id).filter_by(listing_id=listing.id).first() is not None
        if not has_reviews:
            await collect_reviews_for_listing(db, listing, settings)
            collected_any = True
    if collected_any:
        db.commit()


# ── Summary ──────────────────────────────────────────────────────────────
def get_review_summary(db: Session, product: Product, top_n: int = 5, sample_size: int = 10) -> ReviewSummaryOut:
    reviews: list[Review] = [r for listing in product.listings for r in listing.reviews]

    analyzed = [r for r in reviews if r.sentiment is not None]
    total = len(analyzed)
    positive = sum(1 for r in analyzed if r.sentiment == Sentiment.POSITIVE)
    neutral = sum(1 for r in analyzed if r.sentiment == Sentiment.NEUTRAL)
    negative = sum(1 for r in analyzed if r.sentiment == Sentiment.NEGATIVE)

    positive_pct = round(positive / total * 100, 1) if total else None
    neutral_pct = round(neutral / total * 100, 1) if total else None
    negative_pct = round(negative / total * 100, 1) if total else None

    aspect_positive: Counter[str] = Counter()
    aspect_negative: Counter[str] = Counter()
    aspect_mentions: Counter[str] = Counter()

    for r in reviews:
        if not r.review_text:
            continue
        for aspect in _extract_aspects(r.review_text):
            aspect_mentions[aspect] += 1
            if r.sentiment == Sentiment.POSITIVE:
                aspect_positive[aspect] += 1
            elif r.sentiment == Sentiment.NEGATIVE:
                aspect_negative[aspect] += 1

    pros = [
        aspect for aspect, _ in aspect_positive.most_common(top_n)
        if aspect_positive[aspect] > aspect_negative.get(aspect, 0)
    ]
    cons = [
        aspect for aspect, _ in aspect_negative.most_common(top_n)
        if aspect_negative[aspect] >= aspect_positive.get(aspect, 0)
    ]
    most_mentioned = [aspect for aspect, _ in aspect_mentions.most_common(top_n)]
    common_complaints = list(cons)

    retailer_ratings = {
        listing.retailer: listing.rating for listing in product.listings if listing.rating is not None
    }

    sample_reviews = sorted(
        (r for r in reviews if r.review_text),
        key=lambda r: r.collected_at,
        reverse=True,
    )[:sample_size]

    return ReviewSummaryOut(
        product_id=product.id,
        total_reviews_analyzed=total,
        positive_percent=positive_pct,
        neutral_percent=neutral_pct,
        negative_percent=negative_pct,
        pros=pros,
        cons=cons,
        most_mentioned_features=most_mentioned,
        common_complaints=common_complaints,
        retailer_ratings=retailer_ratings,
        sample_reviews=[_review_out(r) for r in sample_reviews],
    )


def _review_out(review: Review) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        retailer=review.listing.retailer,
        reviewer_name=review.reviewer_name,
        rating=review.rating,
        review_title=review.review_title,
        review_text=review.review_text,
        review_date=review.review_date,
        verified_purchase=review.verified_purchase,
        helpful_count=review.helpful_count,
        sentiment=review.sentiment.value if review.sentiment else None,
        sentiment_score=review.sentiment_score,
    )
