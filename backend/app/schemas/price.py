"""API response shapes for price history (Phase 10) and prediction
(Phase 11)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PriceHistoryPoint(BaseModel):
    retailer: str
    price: float
    mrp: float | None
    discount: float | None
    availability: str
    collected_at: datetime

    model_config = {"from_attributes": True}


class ProductPriceHistoryOut(BaseModel):
    """Aggregated across every retailer listing of a product — one combined
    series for the price-history chart, plus the brief's four headline
    figures (highest/lowest/current/average)."""

    product_id: str
    currency: str
    highest: float | None
    lowest: float | None
    current: float | None  # best (lowest) *current* price across retailers
    average: float | None
    points: list[PriceHistoryPoint]


class PricePredictionOut(BaseModel):
    listing_id: str
    retailer: str
    currency: str
    current_price: float | None
    predicted_price: float | None
    predicted_range_low: float | None
    predicted_range_high: float | None
    trend: str  # "UP" | "DOWN" | "STABLE" | "INSUFFICIENT_DATA"
    confidence: float | None
    days_of_history: int
