"""Single-product lookups."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Product
from app.schemas.product import ProductOut
from app.services.search_service import _listing_out


def get_product(db: Session, product_id: str) -> ProductOut | None:
    product = db.get(Product, product_id)
    if product is None:
        return None
    return ProductOut(
        id=product.id,
        common_product_id=product.common_product_id,
        brand=product.brand,
        model=product.model,
        variant=product.variant,
        category=product.category,
        subcategory=product.subcategory,
        canonical_name=product.canonical_name,
        description=product.description,
        specifications=product.specifications or {},
        image_urls=product.image_urls or [],
        listings=[_listing_out(listing) for listing in product.listings],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )
