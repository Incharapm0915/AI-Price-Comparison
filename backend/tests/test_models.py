"""Phase 2 smoke tests: the ORM models round-trip through the real database
with their relationships, JSONB fields, enums, and the pgvector embedding
column all intact."""
from datetime import datetime, timezone

from app.database.models import (
    Availability,
    MatchStatus,
    PriceAlert,
    PriceHistory,
    Product,
    ProductListing,
    Review,
    Sentiment,
    Seller,
)


def test_product_with_listings_price_history_and_reviews_round_trip(db_session):
    product = Product(
        common_product_id="APPLE_IPHONE_15_128_BLACK",
        brand="Apple",
        model="iPhone 15",
        variant="128GB Black",
        category="Electronics",
        subcategory="Smartphones",
        canonical_name="Apple iPhone 15 128GB Black",
        specifications={"display": "6.1 inch", "storage": "128GB"},
        image_urls=["https://example.com/demo/iphone15-black-1.jpg"],
        embedding=[0.01] * 384,
    )
    db_session.add(product)
    db_session.flush()

    seller = Seller(retailer="amazon", seller_name="Appario Retail", seller_rating=4.3, is_verified=True)
    db_session.add(seller)
    db_session.flush()

    listing = ProductListing(
        product_id=product.id,
        retailer="amazon",
        retailer_product_id="B0CHX1W1XY",
        product_name="Apple iPhone 15 (128 GB) - Black",
        product_url="https://example.com/demo/amazon/B0CHX1W1XY",
        brand="Apple",
        model="iPhone 15",
        variant="128GB Black",
        specifications={"display": "6.1 inch", "storage": "128GB"},
        current_price=64999.0,
        mrp=69900.0,
        discount_percent=7.0,
        rating=4.5,
        rating_count=12400,
        review_count=8200,
        rating_breakdown={"1": 100, "2": 150, "3": 400, "4": 3200, "5": 8550},
        availability=Availability.IN_STOCK,
        seller_id=seller.id,
        match_status=MatchStatus.MATCH,
        match_score=0.96,
        match_reason=["same brand", "same model", "same storage", "same color"],
    )
    db_session.add(listing)
    db_session.flush()

    db_session.add(
        PriceHistory(
            listing_id=listing.id,
            price=64999.0,
            mrp=69900.0,
            discount=7.0,
            availability=Availability.IN_STOCK,
            seller="Appario Retail",
        )
    )
    db_session.add(
        Review(
            listing_id=listing.id,
            external_review_id="R1ABCDEF",
            reviewer_name="A. Kumar",
            rating=5.0,
            review_title="Great phone",
            review_text="Camera and performance are excellent.",
            review_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
            verified_purchase=True,
            helpful_count=42,
            sentiment=Sentiment.POSITIVE,
            sentiment_score=0.92,
        )
    )
    db_session.add(
        PriceAlert(listing_id=listing.id, email="buyer@example.com", target_price=60000.0)
    )
    db_session.flush()

    fetched = db_session.get(Product, product.id)
    assert fetched.canonical_name == "Apple iPhone 15 128GB Black"
    assert len(fetched.embedding) == 384
    assert len(fetched.listings) == 1

    fetched_listing = fetched.listings[0]
    assert fetched_listing.retailer == "amazon"
    assert fetched_listing.match_status == MatchStatus.MATCH
    assert fetched_listing.rating_breakdown["5"] == 8550
    assert len(fetched_listing.price_history) == 1
    assert fetched_listing.price_history[0].price == 64999.0
    assert len(fetched_listing.reviews) == 1
    assert fetched_listing.reviews[0].sentiment == Sentiment.POSITIVE
    assert fetched_listing.seller.seller_name == "Appario Retail"


def test_product_can_exist_without_listings_yet(db_session):
    """A freshly-collected, not-yet-matched listing has product_id NULL."""
    listing = ProductListing(
        retailer="flipkart",
        retailer_product_id="MOBGXYZ123",
        product_name="Apple iPhone 15 Black 128 GB",
        product_url="https://example.com/demo/flipkart/MOBGXYZ123",
        availability=Availability.IN_STOCK,
    )
    db_session.add(listing)
    db_session.flush()

    fetched = db_session.get(ProductListing, listing.id)
    assert fetched.product_id is None
    assert fetched.match_status is None
