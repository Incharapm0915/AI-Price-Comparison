"""API response shapes for a single retailer listing."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ListingOut(BaseModel):
    id: str
    retailer: str
    retailer_product_id: str
    product_name: str
    product_url: str
    price: float | None
    mrp: float | None
    discount_percent: float | None
    currency: str
    offers: list[str]
    rating: float | None
    rating_count: int | None
    review_count: int | None
    rating_breakdown: dict[str, int] | None
    availability: str
    seller_name: str | None = None
    seller_rating: float | None = None
    image_urls: list[str]
    specifications: dict
    match_status: str | None
    match_score: float | None
    collected_at: datetime

    model_config = {"from_attributes": True}
