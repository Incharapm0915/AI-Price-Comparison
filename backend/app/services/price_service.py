"""Price history aggregation. Every successful collection records a
PriceHistory row per listing (see search_service._upsert_listing); this
module turns that raw time series into the product-level summary and
chart data the brief's PRICE HISTORY section describes."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.models import PriceHistory, Product, ProductListing
from app.schemas.price import PriceHistoryPoint, ProductPriceHistoryOut


def get_product_price_history(db: Session, product: Product) -> ProductPriceHistoryOut:
    listing_ids = [listing.id for listing in product.listings]
    if not listing_ids:
        return ProductPriceHistoryOut(
            product_id=product.id, currency="INR", highest=None, lowest=None, current=None, average=None, points=[]
        )

    rows: list[PriceHistory] = (
        db.query(PriceHistory)
        .filter(PriceHistory.listing_id.in_(listing_ids))
        .order_by(PriceHistory.collected_at)
        .all()
    )
    if not rows:
        return ProductPriceHistoryOut(
            product_id=product.id, currency="INR", highest=None, lowest=None, current=None, average=None, points=[]
        )

    listing_by_id: dict[str, ProductListing] = {listing.id: listing for listing in product.listings}
    prices = [row.price for row in rows]
    highest = max(prices)
    lowest = min(prices)
    average = round(sum(prices) / len(prices), 2)

    # "Current" = the best (lowest) most-recent price across retailers —
    # matches the brief's example where Flipkart's lower current price is
    # the one shown as "Current" on the product page.
    latest_per_listing: dict[str, PriceHistory] = {}
    for row in rows:
        latest_per_listing[row.listing_id] = row  # rows are ordered ascending, so last write wins
    current = min(row.price for row in latest_per_listing.values()) if latest_per_listing else None

    points = [
        PriceHistoryPoint(
            retailer=listing_by_id[row.listing_id].retailer if row.listing_id in listing_by_id else "unknown",
            price=row.price,
            mrp=row.mrp,
            discount=row.discount,
            availability=row.availability.value,
            collected_at=row.collected_at,
        )
        for row in rows
    ]

    currency = rows[-1].currency if rows else "INR"

    return ProductPriceHistoryOut(
        product_id=product.id,
        currency=currency,
        highest=highest,
        lowest=lowest,
        current=current,
        average=average,
        points=points,
    )


def get_listing_price_series(db: Session, listing_id: str) -> list[PriceHistory]:
    """Raw ascending time series for one listing — used by Phase 11's price
    prediction, which needs per-retailer granularity, not the blended
    product-level view above."""
    return (
        db.query(PriceHistory)
        .filter_by(listing_id=listing_id)
        .order_by(PriceHistory.collected_at)
        .all()
    )
