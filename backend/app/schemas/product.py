"""API response shapes for a canonical (matched) product."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.listing import ListingOut


class ProductOut(BaseModel):
    id: str
    common_product_id: str
    brand: str | None
    model: str | None
    variant: str | None
    category: str | None
    subcategory: str | None
    canonical_name: str
    description: str | None
    specifications: dict
    image_urls: list[str]
    listings: list[ListingOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchResultGroup(BaseModel):
    """One row on the search results page — a canonical product with a
    price summary across however many retailers matched into it."""

    product_id: str
    canonical_name: str
    brand: str | None
    image_url: str | None
    best_price: float | None
    best_price_retailer: str | None
    retailer_count: int
    average_rating: float | None
    total_review_count: int | None
    listings: list[ListingOut]
