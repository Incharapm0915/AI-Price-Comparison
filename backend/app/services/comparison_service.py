"""Builds the side-by-side comparison payload for a matched product —
best price / best rating / best discount / best value badges, per the
brief's COMPARISON PAGE section."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import Product
from app.schemas.comparison import ComparisonOut
from app.services.search_service import _listing_out


def get_comparison(db: Session, product_id: str) -> ComparisonOut | None:
    product = db.get(Product, product_id)
    if product is None:
        return None

    listings = [_listing_out(listing) for listing in product.listings]
    priced = [l for l in listings if l.price is not None]
    rated = [l for l in listings if l.rating is not None]
    discounted = [l for l in listings if l.discount_percent is not None]

    best_price_listing = min(priced, key=lambda l: l.price) if priced else None
    best_rated_listing = max(rated, key=lambda l: l.rating) if rated else None
    best_discount_listing = max(discounted, key=lambda l: l.discount_percent) if discounted else None

    savings = None
    if len(priced) >= 2:
        savings = round(max(l.price for l in priced) - min(l.price for l in priced), 2)

    best_value_listing = None
    if priced:
        cheapest_two = sorted(priced, key=lambda l: l.price)[:2]
        rated_among_cheapest = [l for l in cheapest_two if l.rating is not None]
        best_value_listing = max(rated_among_cheapest, key=lambda l: l.rating) if rated_among_cheapest else cheapest_two[0]

    return ComparisonOut(
        product_id=product.id,
        canonical_name=product.canonical_name,
        brand=product.brand,
        specifications=product.specifications or {},
        image_urls=product.image_urls or [],
        listings=listings,
        best_price_retailer=best_price_listing.retailer if best_price_listing else None,
        best_price=best_price_listing.price if best_price_listing else None,
        savings_vs_highest=savings,
        best_rated_retailer=best_rated_listing.retailer if best_rated_listing else None,
        best_rating=best_rated_listing.rating if best_rated_listing else None,
        best_discount_retailer=best_discount_listing.retailer if best_discount_listing else None,
        best_discount_percent=best_discount_listing.discount_percent if best_discount_listing else None,
        best_value_retailer=best_value_listing.retailer if best_value_listing else None,
    )
