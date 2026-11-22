"""API request/response shapes for price-drop alerts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CreateAlertRequest(BaseModel):
    listing_id: str
    email: EmailStr
    target_price: float = Field(gt=0)


class AlertOut(BaseModel):
    id: str
    listing_id: str
    retailer: str
    product_name: str
    email: str
    target_price: float
    current_price: float | None
    status: str
    triggered_at: datetime | None
    triggered_price: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
