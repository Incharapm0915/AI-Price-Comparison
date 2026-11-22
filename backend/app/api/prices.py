"""GET /api/products/{id}/price-history — aggregated price trend across
every retailer listing of a product.
GET /api/products/{id}/price-prediction — per-retailer price trend estimate."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Product
from app.schemas.price import PricePredictionOut, ProductPriceHistoryOut
from app.services.prediction_service import predict_listing_price
from app.services.price_service import get_product_price_history

router = APIRouter()


@router.get("/{product_id}/price-history", response_model=ProductPriceHistoryOut)
def price_history(product_id: str, db: Session = Depends(get_db)) -> ProductPriceHistoryOut:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})
    return get_product_price_history(db, product)


@router.get("/{product_id}/price-prediction", response_model=list[PricePredictionOut])
def price_prediction(product_id: str, db: Session = Depends(get_db)) -> list[PricePredictionOut]:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail={"code": "PRODUCT_NOT_FOUND", "message": "No product with that id"})
    return [predict_listing_price(db, listing) for listing in product.listings]
