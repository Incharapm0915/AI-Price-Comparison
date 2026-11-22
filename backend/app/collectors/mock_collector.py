"""Mock collectors — `MOCK_MODE=true` (the default). Return realistic,
internally-consistent product/review data with zero live retailer access,
so search, matching, comparison, reviews, and price history are all fully
testable and demoable without depending on Amazon/Flipkart being reachable.

Every URL/ID here is clearly fake (`https://example.com/demo/...`) so mock
data can never be mistaken for a real retailer response.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.collectors.base_collector import BaseCollector
from app.collectors.mock_data import expand_catalog
from app.collectors.types import CollectedListingSummary, CollectedProduct, CollectedReview
from app.utils.logging import get_logger

logger = get_logger(__name__)

_POSITIVE_SNIPPETS = [
    "Camera quality is outstanding, especially in low light.",
    "Battery easily lasts a full day of heavy use.",
    "Display is bright and colours look accurate.",
    "Performance is smooth even with several apps open.",
    "Build quality feels premium for the price.",
    "Great value for money overall.",
    "Sound quality exceeded my expectations.",
    "Extremely comfortable for long sessions.",
    "Setup was quick and the app pairs instantly.",
]
_NEGATIVE_SNIPPETS = [
    "Charging speed is slower than advertised.",
    "Battery drains faster than expected after a couple of months.",
    "Software has occasional lag and stutters.",
    "Packaging was damaged on delivery.",
    "Customer support was slow to respond to my query.",
    "Feels a bit overpriced compared to alternatives.",
]
_NEUTRAL_SNIPPETS = [
    "Does what it says, nothing extraordinary.",
    "Average product for this price range.",
    "Matches the description, no surprises.",
]
_REVIEWER_NAMES = [
    "A. Sharma", "R. Iyer", "Priya K.", "Mohammed A.", "S. Reddy", "Ankit V.",
    "Neha J.", "D. Fernandes", "K. Patel", "Sanjana R.", "Vikram S.", "T. Nair",
]

MOCK_BASE_URL = "https://example.com/demo"


def _day_bucket() -> int:
    """Changes once per day so mock prices drift day-to-day (to build up a
    price history) but stay stable within a single day/demo session."""
    return int(datetime.now(timezone.utc).timestamp() // 86400)


class MockCollector(BaseCollector):
    """One instance per retailer (`retailer="amazon"` or `"flipkart"`)."""

    def __init__(self, retailer: str, settings=None) -> None:
        super().__init__(settings)
        if retailer not in ("amazon", "flipkart"):
            raise ValueError(f"MockCollector supports amazon/flipkart only, got {retailer!r}")
        self.retailer = retailer
        self._catalog = expand_catalog(retailer)

    def _rng_for(self, retailer_product_id: str) -> random.Random:
        return random.Random(f"{self.retailer}:{retailer_product_id}:{_day_bucket()}")

    def _priced_entry(self, entry: dict) -> dict:
        rng = self._rng_for(entry["retailer_product_id"])
        # +/- 6% price jitter per retailer per day, MRP ~10-20% above price.
        jitter = rng.uniform(-0.06, 0.06)
        price = round(entry["base_price"] * (1 + jitter), -1)
        mrp = round(price * rng.uniform(1.08, 1.22), -1)
        discount = round((1 - price / mrp) * 100, 1) if mrp > price else 0.0
        availability_roll = rng.random()
        availability = "IN_STOCK" if availability_roll > 0.08 else ("OUT_OF_STOCK" if availability_roll > 0.03 else "UNAVAILABLE")
        return {**entry, "price": price, "mrp": mrp, "discount_percent": discount, "availability": availability}

    def _product_url(self, retailer_product_id: str) -> str:
        return f"{MOCK_BASE_URL}/{self.retailer}/{retailer_product_id}"

    def _image_urls(self, slug: str) -> list[str]:
        return [f"{MOCK_BASE_URL}/{self.retailer}/images/{slug}-{i}.jpg" for i in range(1, 4)]

    # ── BaseCollector interface ─────────────────────────────────────────
    async def search_products(self, query: str, max_results: int | None = None) -> list[CollectedListingSummary]:
        limit = max_results or self.settings.collector_max_results_per_retailer
        tokens = [t for t in query.lower().split() if t]
        # Require a majority of query tokens to match, not just any single
        # one — otherwise a query like "Samsung Galaxy S24" would also
        # surface an unrelated "Samsung ... Smart TV" on brand-token alone.
        required = max(1, (len(tokens) + 1) // 2)

        def score(entry: dict) -> int:
            haystack = f"{entry['brand']} {entry['model']} {entry['product_name']}".lower()
            return sum(1 for t in tokens if t in haystack)

        scored = [(score(e), e) for e in self._catalog]
        matches = [e for s, e in scored if s >= required]
        matches.sort(key=lambda e: score(e), reverse=True)

        results = []
        for entry in matches[:limit]:
            priced = self._priced_entry(entry)
            results.append(
                CollectedListingSummary(
                    retailer=self.retailer,
                    retailer_product_id=entry["retailer_product_id"],
                    product_name=entry["product_name"],
                    product_url=self._product_url(entry["retailer_product_id"]),
                    price=priced["price"],
                    mrp=priced["mrp"],
                    rating=entry["rating"],
                    rating_count=entry["rating_count"],
                    image_url=self._image_urls(entry["slug"])[0],
                    availability=priced["availability"],
                )
            )
        logger.info("%s: mock search %r -> %d results", self.retailer, query, len(results))
        return results

    async def get_product(self, url: str) -> CollectedProduct:
        retailer_product_id = url.rstrip("/").rsplit("/", 1)[-1]
        entry = next((e for e in self._catalog if e["retailer_product_id"] == retailer_product_id), None)
        if entry is None:
            raise ValueError(f"No mock product for url {url!r}")

        priced = self._priced_entry(entry)
        rng = self._rng_for(retailer_product_id)
        rating_count = entry["rating_count"]
        breakdown_weights = [0.02, 0.03, 0.08, 0.27, 0.60]  # skew positive, like real catalogs
        breakdown = {
            str(star): int(rating_count * w * rng.uniform(0.85, 1.15))
            for star, w in zip(range(1, 6), breakdown_weights)
        }

        product = CollectedProduct(
            retailer=self.retailer,
            retailer_product_id=retailer_product_id,
            product_name=entry["product_name"],
            product_url=url,
            brand=entry["brand"],
            model=entry["model"],
            variant=entry["variant"],
            category=entry["category"],
            subcategory=entry["subcategory"],
            description=f"{entry['product_name']} — {', '.join(entry['highlights'])}." if entry["highlights"] else None,
            highlights=list(entry["highlights"]),
            specifications={k: v for k, v in entry["specifications"].items()},
            image_urls=self._image_urls(entry["slug"]),
            price=priced["price"],
            mrp=priced["mrp"],
            discount_percent=priced["discount_percent"],
            currency="INR",
            offers=(
                ["10% instant discount with select bank cards"] if rng.random() > 0.5 else []
            ),
            availability=priced["availability"],
            rating=entry["rating"],
            rating_count=rating_count,
            review_count=int(rating_count * rng.uniform(0.4, 0.7)),
            rating_breakdown=breakdown,
            seller_name=entry["seller_name"],
            seller_rating=round(rng.uniform(3.8, 4.8), 1),
            seller_review_count=int(rng.uniform(500, 50000)),
            seller_url=f"{MOCK_BASE_URL}/{self.retailer}/seller/{entry['seller_name'].replace(' ', '-').lower()}",
            seller_location=rng.choice(["Bengaluru, IN", "Delhi, IN", "Mumbai, IN", "Chennai, IN", None]),
            identifiers={
                "sku": retailer_product_id,
                **({"asin": retailer_product_id} if self.retailer == "amazon" else {"pid": retailer_product_id}),
            },
        )
        return self.normalize_product(product)

    async def get_reviews(self, url: str, max_reviews: int | None = None) -> list[CollectedReview]:
        retailer_product_id = url.rstrip("/").rsplit("/", 1)[-1]
        entry = next((e for e in self._catalog if e["retailer_product_id"] == retailer_product_id), None)
        if entry is None:
            return []

        limit = min(max_reviews or self.settings.max_reviews_per_product, self.settings.max_reviews_per_product)
        rng = self._rng_for(f"{retailer_product_id}:reviews")
        avg_rating = entry["rating"]
        count = min(limit, rng.randint(8, 30))

        reviews: list[CollectedReview] = []
        for i in range(count):
            rating = max(1, min(5, round(rng.gauss(avg_rating, 0.8))))
            if rating >= 4:
                snippets = rng.sample(_POSITIVE_SNIPPETS, k=min(2, len(_POSITIVE_SNIPPETS)))
            elif rating == 3:
                snippets = rng.sample(_NEUTRAL_SNIPPETS, k=1) + (
                    rng.sample(_NEGATIVE_SNIPPETS, k=1) if rng.random() > 0.5 else []
                )
            else:
                snippets = rng.sample(_NEGATIVE_SNIPPETS, k=min(2, len(_NEGATIVE_SNIPPETS)))

            review_text = " ".join(snippets)
            reviews.append(
                CollectedReview(
                    external_review_id=f"{self.retailer[:2].upper()}{retailer_product_id}-R{i}",
                    reviewer_name=rng.choice(_REVIEWER_NAMES),
                    rating=float(rating),
                    review_title=snippets[0].rstrip(".").split(",")[0],
                    review_text=review_text,
                    review_date=datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 180)),
                    verified_purchase=rng.random() > 0.25,
                    helpful_count=rng.randint(0, 120),
                    review_images=[],
                )
            )
        reviews.sort(key=lambda r: r.review_date, reverse=True)
        return reviews


class MockAmazonCollector(MockCollector):
    def __init__(self, settings=None) -> None:
        super().__init__("amazon", settings)


class MockFlipkartCollector(MockCollector):
    def __init__(self, settings=None) -> None:
        super().__init__("flipkart", settings)
