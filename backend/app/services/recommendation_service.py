"""Product recommendations — two independent, honest signals, since this
project has no account/history system to personalize against:

1. "Recommended for / Not ideal for" — rule-based use-case tags derived
   from the product's own specifications (camera MP, battery mAh, RAM,
   refresh rate) and its AI review summary (Phase 9's pros/cons). A tag
   only ever appears when a concrete signal actually supports it.
2. "Similar products" — other canonical products in the same
   category/subcategory, ranked by embedding similarity (Phase 5), brand
   match, and price proximity. A hard category/subcategory gate keeps
   this from ever suggesting something irrelevant just to fill a list.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.database.models import Product
from app.matching.similarity import cosine_similarity
from app.schemas.recommendation import RecommendationsOut, SimilarProductOut
from app.services.review_service import get_review_summary

_CAMERA_MP_RE = re.compile(r"(\d+)\s*MP", re.IGNORECASE)
_BATTERY_MAH_RE = re.compile(r"(\d+)\s*mAh", re.IGNORECASE)
_RAM_GB_RE = re.compile(r"(\d+)\s*GB", re.IGNORECASE)
_REFRESH_HZ_RE = re.compile(r"(\d+)\s*Hz", re.IGNORECASE)

# Aspect (from Phase 9's review pros/cons) -> use-case label(s).
ASPECT_RECOMMENDED_FOR: dict[str, list[str]] = {
    "Camera": ["Photography"],
    "Performance": ["Gaming", "Multitasking"],
    "Battery": ["Daily use", "Travel"],
    "Display": ["Media & entertainment"],
    "Sound": ["Music & entertainment"],
    "Build Quality": ["Rugged/heavy use"],
    "Comfort": ["Extended wear"],
}
ASPECT_NOT_IDEAL_FOR: dict[str, list[str]] = {
    "Battery": ["Multi-day use without access to a charger"],
    "Price": ["Budget-conscious buyers"],
    "Software": ["Users who dislike frequent software updates"],
    "Performance": ["Heavy multitasking or demanding gaming"],
    "Camera": ["Serious photography"],
    "Build Quality": ["Rough/outdoor daily use"],
    "Customer Support": ["Buyers who value fast after-sales support"],
}

_SIMILAR_PRODUCTS_SCAN_LIMIT = 50


def _spec_signals(specifications: dict) -> dict[str, float]:
    """Scans every spec value for known numeric patterns, regardless of
    which key they're filed under (retailers name keys inconsistently)."""
    signals: dict[str, float] = {}
    for value in specifications.values():
        text = str(value)
        for pattern, signal_name in (
            (_CAMERA_MP_RE, "camera_mp"),
            (_BATTERY_MAH_RE, "battery_mah"),
            (_RAM_GB_RE, "ram_gb"),
            (_REFRESH_HZ_RE, "refresh_hz"),
        ):
            match = pattern.search(text)
            if match:
                signals[signal_name] = max(signals.get(signal_name, 0.0), float(match.group(1)))
    return signals


def get_use_case_recommendations(db: Session, product: Product) -> tuple[list[str], list[str]]:
    recommended: list[str] = []
    not_ideal: list[str] = []

    signals = _spec_signals(product.specifications or {})
    if signals.get("camera_mp", 0) >= 40:
        recommended.append("Photography")
    if signals.get("ram_gb", 0) >= 8 or signals.get("refresh_hz", 0) >= 90:
        recommended.append("Gaming")
    if signals.get("battery_mah", 0) >= 4000:
        recommended.append("Daily use")
    if 0 < signals.get("battery_mah", 0) < 3000:
        not_ideal.append("Multi-day use without access to a charger")

    summary = get_review_summary(db, product)
    for aspect in summary.pros:
        for label in ASPECT_RECOMMENDED_FOR.get(aspect, []):
            if label not in recommended:
                recommended.append(label)
    for aspect in summary.cons:
        for label in ASPECT_NOT_IDEAL_FOR.get(aspect, []):
            if label not in not_ideal:
                not_ideal.append(label)

    return recommended[:5], not_ideal[:5]


def _best_price(product: Product) -> float | None:
    prices = [l.current_price for l in product.listings if l.current_price is not None]
    return min(prices) if prices else None


def get_similar_products(db: Session, product: Product, limit: int = 6) -> list[Product]:
    if not product.category:
        return []

    query = db.query(Product).filter(Product.category == product.category, Product.id != product.id)
    if product.subcategory:
        query = query.filter(Product.subcategory == product.subcategory)
    candidates = query.limit(_SIMILAR_PRODUCTS_SCAN_LIMIT).all()

    source_price = _best_price(product)
    scored: list[tuple[float, Product]] = []
    for candidate in candidates:
        score = 0.0
        if candidate.brand and product.brand and candidate.brand.lower() == product.brand.lower():
            score += 0.2
        if product.embedding is not None and candidate.embedding is not None:
            score += 0.6 * cosine_similarity(list(product.embedding), list(candidate.embedding))
        candidate_price = _best_price(candidate)
        if source_price and candidate_price:
            diff_ratio = abs(source_price - candidate_price) / max(source_price, candidate_price)
            score += 0.2 * max(0.0, 1 - diff_ratio)
        scored.append((score, candidate))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [candidate for _, candidate in scored[:limit]]


def get_recommendations(db: Session, product: Product) -> RecommendationsOut:
    recommended_for, not_ideal_for = get_use_case_recommendations(db, product)
    similar = get_similar_products(db, product)

    return RecommendationsOut(
        product_id=product.id,
        recommended_for=recommended_for,
        not_ideal_for=not_ideal_for,
        similar_products=[_similar_out(p) for p in similar],
    )


def _similar_out(product: Product) -> SimilarProductOut:
    ratings = [l.rating for l in product.listings if l.rating is not None]
    return SimilarProductOut(
        product_id=product.id,
        canonical_name=product.canonical_name,
        brand=product.brand,
        image_url=(product.image_urls or [None])[0],
        best_price=_best_price(product),
        average_rating=round(sum(ratings) / len(ratings), 2) if ratings else None,
    )
