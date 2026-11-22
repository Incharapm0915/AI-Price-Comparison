"""Celery tasks: collect_search_results, collect_product, collect_reviews,
run_product_matching. Each task owns its own DB session (Celery workers
are separate processes from the API, so there's no request-scoped session
to reuse) and commits/closes it itself.
"""
from __future__ import annotations

import asyncio

from app.database.connection import SessionLocal
from app.database.models import Product, ProductListing
from app.matching.product_matcher import MatchCandidate, ProductMatcher
from app.services.review_service import collect_reviews_for_listing
from app.services.search_service import refresh_listing, run_search
from app.utils.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.collection_tasks.collect_search_results_task", bind=True, max_retries=2)
def collect_search_results_task(self, query: str, retailers: list[str] | None = None) -> dict:
    db = SessionLocal()
    try:
        result = asyncio.run(run_search(db, query, retailers=retailers))
        logger.info("collect_search_results_task: %r -> %d groups", query, len(result.groups))
        return {"query": query, "groups": len(result.groups), "retailers_failed": result.retailers_failed}
    finally:
        db.close()


@celery_app.task(name="app.workers.collection_tasks.collect_product_task", bind=True, max_retries=2)
def collect_product_task(self, listing_id: str) -> dict:
    db = SessionLocal()
    try:
        listing = db.get(ProductListing, listing_id)
        if listing is None:
            return {"listing_id": listing_id, "status": "not_found"}
        ok = asyncio.run(refresh_listing(db, listing))
        db.commit()
        return {"listing_id": listing_id, "status": "refreshed" if ok else "failed"}
    finally:
        db.close()


@celery_app.task(name="app.workers.collection_tasks.collect_reviews_task", bind=True, max_retries=2)
def collect_reviews_task(self, listing_id: str) -> dict:
    db = SessionLocal()
    try:
        listing = db.get(ProductListing, listing_id)
        if listing is None:
            return {"listing_id": listing_id, "status": "not_found"}
        count = asyncio.run(collect_reviews_for_listing(db, listing))
        db.commit()
        return {"listing_id": listing_id, "reviews_collected": count}
    finally:
        db.close()


@celery_app.task(name="app.workers.collection_tasks.run_product_matching_task")
def run_product_matching_task(product_id: str) -> dict:
    """Re-scores every pair of listings currently attached to a product —
    useful after normalizer/matcher logic changes, to re-verify a group's
    integrity without a full re-collection."""
    db = SessionLocal()
    try:
        product = db.get(Product, product_id)
        if product is None:
            return {"product_id": product_id, "status": "not_found"}

        matcher = ProductMatcher()
        candidates = [
            MatchCandidate(
                key=listing.id,
                title=listing.product_name,
                identifiers=listing.identifiers or {},
                specifications=listing.specifications or {},
            )
            for listing in product.listings
        ]
        if len(candidates) < 2:
            return {"product_id": product_id, "status": "skipped_single_listing"}

        grouping = matcher.group(candidates)
        by_id = {listing.id: listing for listing in product.listings}
        updated = 0
        for pair, result in grouping.pairwise_results.items():
            for listing_id in pair:
                listing = by_id[listing_id]
                if result.status.value == "MATCH":
                    listing.match_status = result.status
                    listing.match_score = result.score
                    listing.match_reason = result.reasons[:10]
                    updated += 1
        db.commit()
        return {"product_id": product_id, "listings_updated": updated}
    finally:
        db.close()
