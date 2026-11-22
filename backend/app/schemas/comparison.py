"""API response shape for the side-by-side comparison page."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.listing import ListingOut


class ComparisonOut(BaseModel):
    product_id: str
    canonical_name: str
    brand: str | None
    specifications: dict
    image_urls: list[str]
    listings: list[ListingOut]

    best_price_retailer: str | None
    best_price: float | None
    savings_vs_highest: float | None  # highest listed price - best price

    best_rated_retailer: str | None
    best_rating: float | None

    best_discount_retailer: str | None
    best_discount_percent: float | None

    # "Best overall value" — highest rated among the two cheapest listings,
    # falling back to best price when there's a single listing.
    best_value_retailer: str | None
