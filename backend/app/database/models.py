"""SQLAlchemy ORM models.

Five core tables per the project's database design:
`Product` (canonical/matched product), `ProductListing` (one retailer's listing
of a Product), `PriceHistory`, `Review`, `Seller` — plus `PriceAlert` to back
the price-drop-alert feature. All JSON-shaped fields (specifications, images,
offers, review images) use JSONB so retailer-specific data never has to be
force-fit into rigid columns.
"""
import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

# Dimensionality of the sentence-transformers model configured via
# EMBEDDING_MODEL_NAME (all-MiniLM-L6-v2 -> 384). If that setting ever
# changes to a model with a different output size, this constant and the
# embedding column must be migrated together.
EMBEDDING_DIM = 384


class Availability(str, enum.Enum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class MatchStatus(str, enum.Enum):
    MATCH = "MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NO_MATCH = "NO_MATCH"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Sentiment(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    TRIGGERED = "TRIGGERED"
    DELETED = "DELETED"


def _uuid() -> str:
    return str(uuid.uuid4())


class Product(Base):
    """The canonical/common product a search result group represents —
    platform-agnostic. Created once multiple retailer listings are matched
    together (or once, for a single-retailer listing with no match yet)."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Human-readable natural key, e.g. "APPLE_IPHONE_15_128_BLACK".
    common_product_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    brand: Mapped[str | None] = mapped_column(String(120), index=True)
    model: Mapped[str | None] = mapped_column(String(255), index=True)
    variant: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120))
    canonical_name: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    specifications: Mapped[dict] = mapped_column(JSONB, default=dict)
    image_urls: Mapped[list] = mapped_column(JSONB, default=list)

    # Sentence-transformer embedding of brand + model + canonical name + key
    # specs, used for Stage 4 semantic matching (see app/matching/).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listings: Mapped[list["ProductListing"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_products_brand_model", "brand", "model"),)


class Seller(Base):
    """A retailer-side seller/merchant. Deliberately holds no auth/payment
    data — public storefront info only."""

    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    retailer: Mapped[str] = mapped_column(String(50), index=True)
    external_seller_id: Mapped[str | None] = mapped_column(String(255))
    seller_name: Mapped[str] = mapped_column(String(255))
    seller_url: Mapped[str | None] = mapped_column(String(1000))
    seller_rating: Mapped[float | None] = mapped_column(Float)
    seller_review_count: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("retailer", "external_seller_id", name="uq_seller_retailer_external_id"),
    )


class ProductListing(Base):
    """One retailer's listing of a `Product` — the Amazon row, the Flipkart
    row, etc. Collected verbatim (post-normalization) from that retailer;
    never merged with another retailer's data at this level."""

    __tablename__ = "product_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=True
    )

    retailer: Mapped[str] = mapped_column(String(50), index=True)
    retailer_product_id: Mapped[str] = mapped_column(String(255), index=True)  # ASIN / PID / SKU
    product_name: Mapped[str] = mapped_column(String(500))
    product_url: Mapped[str] = mapped_column(String(1000))

    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(255))
    variant: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    specifications: Mapped[dict] = mapped_column(JSONB, default=dict)
    image_urls: Mapped[list] = mapped_column(JSONB, default=list)

    # Identifiers used in Stage 1 matching, when the retailer exposes them.
    identifiers: Mapped[dict] = mapped_column(JSONB, default=dict)  # {gtin, ean, upc, mpn, sku}

    # Latest known pricing snapshot (a denormalized cache of the newest
    # PriceHistory row for this listing — cheap reads for search/comparison
    # views; PriceHistory remains the source of truth for trends).
    current_price: Mapped[float | None] = mapped_column(Float)
    mrp: Mapped[float | None] = mapped_column(Float)
    discount_percent: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    offers: Mapped[list] = mapped_column(JSONB, default=list)  # coupons/bank offers, if displayed

    rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int | None] = mapped_column(Integer)
    review_count: Mapped[int | None] = mapped_column(Integer)
    rating_breakdown: Mapped[dict | None] = mapped_column(JSONB)  # {"1":n,"2":n,...,"5":n}

    availability: Mapped[Availability] = mapped_column(
        Enum(Availability, name="availability"), default=Availability.UNKNOWN
    )

    seller_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sellers.id"), nullable=True)

    # How this listing was assigned to `product_id` (NULL until matching runs).
    match_status: Mapped[MatchStatus | None] = mapped_column(Enum(MatchStatus, name="match_status"))
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reason: Mapped[list | None] = mapped_column(JSONB)

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product | None"] = relationship(back_populates="listings")
    seller: Mapped["Seller | None"] = relationship()
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="PriceHistory.collected_at"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("retailer", "retailer_product_id", name="uq_listing_retailer_product_id"),
        Index("ix_listings_product_retailer", "product_id", "retailer"),
    )


class PriceHistory(Base):
    """A single price snapshot for a listing, recorded on every successful
    collection. Powers the price-history chart and prediction model."""

    __tablename__ = "price_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_listings.id", ondelete="CASCADE"), index=True
    )

    price: Mapped[float] = mapped_column(Float)
    mrp: Mapped[float | None] = mapped_column(Float)
    discount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    availability: Mapped[Availability] = mapped_column(
        Enum(Availability, name="availability"), default=Availability.UNKNOWN
    )
    seller: Mapped[str | None] = mapped_column(String(255))

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped["ProductListing"] = relationship(back_populates="price_history")

    __table_args__ = (Index("ix_price_history_listing_collected", "listing_id", "collected_at"),)


class Review(Base):
    """A review attached to a specific retailer listing. Any field the
    retailer doesn't expose is left NULL — never fabricated."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_listings.id", ondelete="CASCADE"), index=True
    )
    external_review_id: Mapped[str | None] = mapped_column(String(255))

    reviewer_name: Mapped[str | None] = mapped_column(String(255))
    rating: Mapped[float | None] = mapped_column(Float)
    review_title: Mapped[str | None] = mapped_column(String(500))
    review_text: Mapped[str | None] = mapped_column(Text)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_purchase: Mapped[bool | None] = mapped_column(Boolean)
    helpful_count: Mapped[int | None] = mapped_column(Integer)
    review_images: Mapped[list] = mapped_column(JSONB, default=list)

    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment, name="sentiment"))
    sentiment_score: Mapped[float | None] = mapped_column(Float)

    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped["ProductListing"] = relationship(back_populates="reviews")

    __table_args__ = (
        UniqueConstraint(
            "listing_id", "external_review_id", name="uq_review_listing_external_id"
        ),
    )


class PriceAlert(Base):
    """A user-defined target price for a listing. No account system exists
    in this project, so alerts are addressed by email directly rather than
    a user_id foreign key."""

    __tablename__ = "price_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    listing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("product_listings.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    target_price: Mapped[float] = mapped_column(Float)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, name="alert_status"), default=AlertStatus.ACTIVE)

    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    triggered_price: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listing: Mapped["ProductListing"] = relationship()

    __table_args__ = (Index("ix_price_alerts_email_status", "email", "status"),)
