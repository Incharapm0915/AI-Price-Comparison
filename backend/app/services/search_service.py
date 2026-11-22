"""Orchestrates the full user-search flow:

    collect (per retailer, concurrent) -> normalize -> match/group -> persist -> respond

One retailer failing (blocked, timed out, denied) never crashes the whole
search — its results are just omitted and reported in `retailers_failed`.
Likewise one product page failing never drops the rest of that retailer's
results.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.collectors.collector_factory import CollectorFactory, SUPPORTED_RETAILERS
from app.collectors.types import CollectedProduct, CollectorError
from app.config import Settings, get_settings
from app.database.models import Availability, MatchStatus, PriceHistory, Product, ProductListing, Seller
from app.matching.normalizer import ProductNormalizer
from app.matching.product_matcher import MatchCandidate, ProductMatcher
from app.schemas.listing import ListingOut
from app.schemas.product import SearchResultGroup
from app.schemas.search import SearchResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

# How many product-detail pages to fetch concurrently per retailer. Even
# though mock collectors don't need it, live collectors do — this keeps
# request bursts within "reasonable rate" regardless of collector type.
_PRODUCT_FETCH_CONCURRENCY = 3


class _Candidate:
    """A collected product paired with the key used to track it through
    matching/grouping/persistence."""

    __slots__ = ("key", "retailer", "product")

    def __init__(self, key: str, retailer: str, product: CollectedProduct):
        self.key = key
        self.retailer = retailer
        self.product = product


async def run_search(
    db: Session,
    query: str,
    retailers: list[str] | None = None,
    max_results_per_retailer: int | None = None,
    settings: Settings | None = None,
    matcher: ProductMatcher | None = None,
) -> SearchResponse:
    settings = settings or get_settings()
    matcher = matcher or ProductMatcher(settings=settings)
    query = query.strip()
    retailer_names = retailers or list(SUPPORTED_RETAILERS)

    collected: list[_Candidate] = []
    retailers_searched: list[str] = []
    retailers_failed: list[str] = []

    retailer_results = await asyncio.gather(
        *[_collect_from_retailer(name, query, max_results_per_retailer, settings) for name in retailer_names],
        return_exceptions=True,
    )

    for name, result in zip(retailer_names, retailer_results):
        if isinstance(result, Exception):
            logger.warning("%s: search failed entirely: %s", name, result)
            retailers_failed.append(name)
            continue
        retailers_searched.append(name)
        for i, product in enumerate(result):
            collected.append(_Candidate(key=f"{name}:{i}:{product.retailer_product_id}", retailer=name, product=product))

    if not collected:
        return SearchResponse(query=query, groups=[], retailers_searched=retailers_searched, retailers_failed=retailers_failed)

    candidates = [
        MatchCandidate(
            key=c.key,
            title=c.product.product_name,
            identifiers=c.product.identifiers,
            specifications=c.product.specifications,
        )
        for c in collected
    ]
    grouping = matcher.group(candidates)
    by_key = {c.key: c for c in collected}

    groups: list[SearchResultGroup] = []
    for group in grouping.groups:
        members = [by_key[k] for k in group.members]
        product = _persist_group(db, members, group.pairwise_results)
        groups.append(_build_search_result_group(product))

    db.commit()

    groups.sort(key=lambda g: (-g.retailer_count, g.best_price if g.best_price is not None else float("inf")))
    return SearchResponse(query=query, groups=groups, retailers_searched=retailers_searched, retailers_failed=retailers_failed)


async def _collect_from_retailer(
    retailer: str, query: str, max_results: int | None, settings: Settings
) -> list[CollectedProduct]:
    collector = CollectorFactory.get(retailer, settings)
    try:
        summaries = await collector.search_products(query, max_results)
    except CollectorError as exc:
        logger.warning("%s: search_products failed: %s", retailer, exc)
        raise

    semaphore = asyncio.Semaphore(_PRODUCT_FETCH_CONCURRENCY)

    async def fetch(url: str) -> CollectedProduct | None:
        async with semaphore:
            try:
                return await collector.get_product(url)
            except CollectorError as exc:
                logger.warning("%s: get_product(%s) failed, skipping this listing: %s", retailer, url, exc)
                return None

    products = await asyncio.gather(*[fetch(s.product_url) for s in summaries])
    return [p for p in products if p is not None and collector.validate_product(p)]


def _persist_group(db: Session, members: list[_Candidate], pairwise: dict) -> Product:
    normalizer = ProductNormalizer()
    representative = members[0].product
    normalized = normalizer.normalize(representative.product_name)

    common_product_id = ProductNormalizer.build_common_product_id(
        normalized.brand or representative.brand,
        normalized.model or representative.model,
        normalized.storage_gb,
        normalized.color or representative.variant,
    )

    product = db.query(Product).filter_by(common_product_id=common_product_id).one_or_none()
    if product is None:
        product = Product(
            common_product_id=common_product_id,
            brand=normalized.brand or representative.brand,
            model=normalized.model or representative.model,
            variant=representative.variant,
            category=representative.category,
            subcategory=representative.subcategory,
            canonical_name=representative.product_name,
            description=representative.description,
        )
        db.add(product)

    merged_specs: dict = dict(product.specifications or {})
    merged_images: list[str] = list(product.image_urls or [])
    for member in members:
        for k, v in member.product.specifications.items():
            merged_specs.setdefault(k, v)
        for url in member.product.image_urls:
            if url not in merged_images:
                merged_images.append(url)
    product.specifications = merged_specs
    product.image_urls = merged_images
    if not product.description and representative.description:
        product.description = representative.description

    db.flush()  # assign product.id

    is_multi = len(members) > 1
    for member in members:
        _upsert_listing(db, product, member, pairwise, is_multi)

    return product


def _upsert_listing(db: Session, product: Product, member: _Candidate, pairwise: dict, is_multi: bool) -> None:
    data = member.product
    listing = (
        db.query(ProductListing)
        .filter_by(retailer=data.retailer, retailer_product_id=data.retailer_product_id)
        .one_or_none()
    )
    if listing is None:
        listing = ProductListing(retailer=data.retailer, retailer_product_id=data.retailer_product_id)
        db.add(listing)

    listing.product_id = product.id
    _apply_collected_data(db, listing, data)

    if is_multi:
        scores = [r.score for pair, r in pairwise.items() if member.key in pair and r.status == MatchStatus.MATCH]
        listing.match_status = MatchStatus.MATCH
        listing.match_score = max(scores) if scores else None
        reasons = [reason for pair, r in pairwise.items() if member.key in pair for reason in r.reasons]
        listing.match_reason = reasons[:10] or None
    else:
        listing.match_status = None
        listing.match_score = None
        listing.match_reason = None

    db.flush()


def _apply_collected_data(db: Session, listing: ProductListing, data: CollectedProduct) -> None:
    """Copies a freshly-collected product's fields onto an existing (or
    brand-new) listing row and records a PriceHistory point. Shared by the
    initial search flow and background refresh jobs (Phase 12) — anything
    that re-collects an existing listing goes through this, so a price
    point is recorded every time, consistently."""
    listing.product_name = data.product_name
    listing.product_url = data.product_url
    listing.brand = data.brand
    listing.model = data.model
    listing.variant = data.variant
    listing.description = data.description
    listing.specifications = data.specifications
    listing.image_urls = data.image_urls
    listing.identifiers = data.identifiers
    listing.current_price = data.price
    listing.mrp = data.mrp
    listing.discount_percent = data.discount_percent
    listing.currency = data.currency
    listing.offers = data.offers
    listing.rating = data.rating
    listing.rating_count = data.rating_count
    listing.review_count = data.review_count
    listing.rating_breakdown = data.rating_breakdown
    try:
        listing.availability = Availability(data.availability)
    except ValueError:
        listing.availability = Availability.UNKNOWN

    if data.seller_name:
        listing.seller = _upsert_seller(db, data)

    # Explicit, not relied on as a DB-side onupdate trigger — this is what
    # "staleness" (refresh_stale_listings_task) is measured against.
    listing.collected_at = datetime.now(timezone.utc)

    db.flush()

    db.add(
        PriceHistory(
            listing_id=listing.id,
            price=data.price or 0.0,
            mrp=data.mrp,
            discount=data.discount_percent,
            currency=data.currency,
            availability=listing.availability,
            seller=data.seller_name,
        )
    )


async def refresh_listing(db: Session, listing: ProductListing, settings: Settings | None = None) -> bool:
    """Re-collects a single already-known listing (price/rating/spec
    refresh, no re-matching) — used by background jobs (Phase 12), not the
    initial search flow. Returns False and leaves the listing untouched if
    collection fails, per the "one failure doesn't crash the run" rule."""
    settings = settings or get_settings()
    collector = CollectorFactory.get(listing.retailer, settings)
    try:
        data = await collector.get_product(listing.product_url)
    except CollectorError as exc:
        logger.warning("%s: refresh failed for listing %s: %s", listing.retailer, listing.id, exc)
        return False

    if not collector.validate_product(data):
        return False

    _apply_collected_data(db, listing, data)
    return True


def _upsert_seller(db: Session, data: CollectedProduct) -> Seller:
    # Collectors don't reliably expose a true external seller ID, so the
    # seller's display name is used as a pragmatic fallback key, scoped per
    # retailer (a real seller ID would replace this if a retailer exposes one).
    external_id = data.seller_name
    seller = db.query(Seller).filter_by(retailer=data.retailer, external_seller_id=external_id).one_or_none()
    if seller is None:
        seller = Seller(retailer=data.retailer, external_seller_id=external_id, seller_name=data.seller_name)
        db.add(seller)
        db.flush()
    seller.seller_rating = data.seller_rating if data.seller_rating is not None else seller.seller_rating
    seller.seller_review_count = data.seller_review_count if data.seller_review_count is not None else seller.seller_review_count
    seller.seller_url = data.seller_url or seller.seller_url
    seller.location = data.seller_location or seller.location
    return seller


def _build_search_result_group(product: Product) -> SearchResultGroup:
    listings = [_listing_out(listing) for listing in product.listings]
    priced = [l for l in listings if l.price is not None]
    best = min(priced, key=lambda l: l.price) if priced else None
    ratings = [l.rating for l in listings if l.rating is not None]
    review_counts = [l.review_count for l in listings if l.review_count is not None]

    return SearchResultGroup(
        product_id=product.id,
        canonical_name=product.canonical_name,
        brand=product.brand,
        image_url=(product.image_urls or [None])[0] or (listings[0].image_urls[0] if listings and listings[0].image_urls else None),
        best_price=best.price if best else None,
        best_price_retailer=best.retailer if best else None,
        retailer_count=len({l.retailer for l in listings}),
        average_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
        total_review_count=sum(review_counts) if review_counts else None,
        listings=listings,
    )


def _listing_out(listing: ProductListing) -> ListingOut:
    return ListingOut(
        id=listing.id,
        retailer=listing.retailer,
        retailer_product_id=listing.retailer_product_id,
        product_name=listing.product_name,
        product_url=listing.product_url,
        price=listing.current_price,
        mrp=listing.mrp,
        discount_percent=listing.discount_percent,
        currency=listing.currency,
        offers=listing.offers or [],
        rating=listing.rating,
        rating_count=listing.rating_count,
        review_count=listing.review_count,
        rating_breakdown=listing.rating_breakdown,
        availability=listing.availability.value,
        seller_name=listing.seller.seller_name if listing.seller else None,
        seller_rating=listing.seller.seller_rating if listing.seller else None,
        image_urls=listing.image_urls or [],
        specifications=listing.specifications or {},
        match_status=listing.match_status.value if listing.match_status else None,
        match_score=listing.match_score,
        collected_at=listing.collected_at,
    )
