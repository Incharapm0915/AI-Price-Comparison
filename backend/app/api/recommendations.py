"""GET /api/products/{id}/recommendations — use-case tags + similar
products."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Product
from app.schemas.recommendation import RecommendationsOut
from app.services.recommendation_service import get_recommendations

router = APIRouter()


@router.get("/{product_id}/recommendations", response_model=RecommendationsOut)
def recommendations(product_id: str, db: Session = Depends(get_db)) -> RecommendationsOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})
    return get_recommendations(db, product)
