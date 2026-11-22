"""API response shapes for reviews and the AI-generated summary."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ReviewOut(BaseModel):
    id: str
    retailer: str
    reviewer_name: str | None
    rating: float | None
    review_title: str | None
    review_text: str | None
    review_date: datetime | None
    verified_purchase: bool | None
    helpful_count: int | None
    sentiment: str | None
    sentiment_score: float | None


class ReviewSummaryOut(BaseModel):
    product_id: str
    total_reviews_analyzed: int
    positive_percent: float | None
    neutral_percent: float | None
    negative_percent: float | None

    pros: list[str]
    cons: list[str]
    most_mentioned_features: list[str]
    common_complaints: list[str]

    retailer_ratings: dict[str, float]
    sample_reviews: list[ReviewOut]
