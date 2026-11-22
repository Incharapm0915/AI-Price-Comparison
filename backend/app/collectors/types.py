"""Shared data shapes and exceptions for every collector (mock or live).

These are plain dataclasses rather than Pydantic/ORM models deliberately —
this is the raw, pre-normalization shape a collector hands back. Phase 4's
normalizer and Phase 8's services turn this into DB rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class CollectorError(Exception):
    """Base class for collector failures. Callers must catch this per-listing
    so one failed product never crashes an entire search (see spec's
    ERROR HANDLING section)."""


class CollectorAccessDeniedError(CollectorError):
    """Raised when a retailer denies automated access (CAPTCHA, block page,
    robots.txt disallow, HTTP 403/429, ...). The collector must stop
    gracefully and surface this rather than retrying aggressively or trying
    to circumvent the block."""


class CollectorParseError(CollectorError):
    """Raised when a page loaded successfully but expected elements were
    missing/changed — a broken parser, not a bot-block."""


@dataclass
class CollectedListingSummary:
    """One row of a retailer search-results page — enough to decide whether
    to visit the product page, not the full detail."""

    retailer: str
    retailer_product_id: str
    product_name: str
    product_url: str
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | None = None
    image_url: str | None = None
    availability: str | None = None


@dataclass
class CollectedProduct:
    """Full detail scraped/generated for a single retailer listing —
    mirrors the "PRODUCT DATA TO EXTRACT" section of the brief. Any field
    the source doesn't expose stays None/empty rather than being guessed."""

    retailer: str
    retailer_product_id: str
    product_name: str
    product_url: str

    brand: str | None = None
    model: str | None = None
    variant: str | None = None
    category: str | None = None
    subcategory: str | None = None

    description: str | None = None
    highlights: list[str] = field(default_factory=list)
    specifications: dict[str, str] = field(default_factory=dict)
    image_urls: list[str] = field(default_factory=list)

    price: float | None = None
    mrp: float | None = None
    discount_percent: float | None = None
    currency: str = "INR"
    offers: list[str] = field(default_factory=list)
    availability: str = "UNKNOWN"

    rating: float | None = None
    rating_count: int | None = None
    review_count: int | None = None
    rating_breakdown: dict[str, int] | None = None

    seller_name: str | None = None
    seller_rating: float | None = None
    seller_review_count: int | None = None
    seller_url: str | None = None
    seller_location: str | None = None

    # GTIN/EAN/UPC/MPN/SKU/ASIN — whichever the retailer exposes.
    identifiers: dict[str, str] = field(default_factory=dict)

    collected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CollectedReview:
    external_review_id: str | None = None
    reviewer_name: str | None = None
    rating: float | None = None
    review_title: str | None = None
    review_text: str | None = None
    review_date: datetime | None = None
    verified_purchase: bool | None = None
    helpful_count: int | None = None
    review_images: list[str] = field(default_factory=list)
