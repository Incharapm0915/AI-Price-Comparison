"""GET /api/products/{id}/reviews — collects reviews on first access (if
none are stored yet), then returns the AI sentiment/pros-cons summary."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Product
from app.schemas.review import ReviewSummaryOut
from app.services.review_service import ensure_reviews_collected, get_review_summary

router = APIRouter()


@router.get("/{product_id}/reviews", response_model=ReviewSummaryOut)
async def get_reviews(product_id: str, db: Session = Depends(get_db)) -> ReviewSummaryOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})

    await ensure_reviews_collected(db, product)
    db.refresh(product)
    return get_review_summary(db, product)
