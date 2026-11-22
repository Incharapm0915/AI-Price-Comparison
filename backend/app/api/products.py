"""GET /api/products/{id} — canonical product detail."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.product import ProductOut
from app.services.product_service import get_product

router = APIRouter()


@router.get("/{product_id}", response_model=ProductOut)
def get_product_detail(product_id: str, db: Session = Depends(get_db)) -> ProductOut:
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})
    return product
