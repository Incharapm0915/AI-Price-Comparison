"""API response shapes for product recommendations."""
from __future__ import annotations

from pydantic import BaseModel


class SimilarProductOut(BaseModel):
    product_id: str
    canonical_name: str
    brand: str | None
    image_url: str | None
    best_price: float | None
    average_rating: float | None


class RecommendationsOut(BaseModel):
    product_id: str
    recommended_for: list[str]
    not_ideal_for: list[str]
    similar_products: list[SimilarProductOut]
