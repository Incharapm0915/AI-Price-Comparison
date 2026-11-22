"""GET /api/products/{id}/compare — side-by-side retailer comparison."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.comparison import ComparisonOut
from app.services.comparison_service import get_comparison

router = APIRouter()


@router.get("/{product_id}/compare", response_model=ComparisonOut)
def compare(product_id: str, db: Session = Depends(get_db)) -> ComparisonOut:
    comparison = get_comparison(db, product_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})
    return comparison
