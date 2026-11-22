"""One-off, manual smoke test against the real Amazon/Flipkart sites.

NOT part of the automated test suite on purpose — hitting live retailer
sites shouldn't happen on every CI run (that violates the project's own
"use reasonable request rates" policy and would make CI flaky/network-
dependent). Run this by hand, occasionally, to sanity-check the live
adapters still work against the real markup:

    python scripts/live_collector_smoke_test.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.collectors.amazon_collector import AmazonCollector
from app.collectors.flipkart_collector import FlipkartCollector
from app.collectors.playwright_manager import PlaywrightManager
from app.collectors.types import CollectorAccessDeniedError, CollectorParseError
from app.config import Settings


async def try_collector(name: str, collector, query: str) -> None:
    print(f"\n=== {name}: search_products({query!r}) ===")
    try:
        results = await collector.search_products(query, max_results=3)
        if not results:
            print("  -> 0 results (search ran, but nothing matched or markup didn't parse)")
            return
        for r in results:
            print(f"  - {r.product_name!r} | price={r.price} | rating={r.rating} | url={r.product_url}")

        print(f"\n=== {name}: get_product({results[0].product_url!r}) ===")
        product = await collector.get_product(results[0].product_url)
        print(f"  name={product.product_name!r}")
        print(f"  price={product.price} mrp={product.mrp} discount={product.discount_percent}")
        print(f"  rating={product.rating} rating_count={product.rating_count}")
        print(f"  availability={product.availability}")
        print(f"  specifications ({len(product.specifications)} keys): {list(product.specifications.items())[:5]}")
        print(f"  images: {len(product.image_urls)}")

        print(f"\n=== {name}: get_reviews(...) ===")
        reviews = await collector.get_reviews(results[0].product_url, max_reviews=5)
        print(f"  -> {len(reviews)} reviews")
        for rv in reviews[:2]:
            print(f"  - {rv.reviewer_name!r} ({rv.rating}): {(rv.review_text or '')[:80]!r}")

    except CollectorAccessDeniedError as exc:
        print(f"  BLOCKED (access denied, stopped gracefully as designed): {exc}")
    except CollectorParseError as exc:
        print(f"  PARSE FAILURE (site structure differs from selectors, or content genuinely empty): {exc}")
    except Exception as exc:
        print(f"  UNEXPECTED ERROR: {type(exc).__name__}: {exc}")


async def main() -> None:
    settings = Settings(
        mock_mode=False,
        collector_max_retries=0,  # don't hammer the site while diagnosing
        collector_min_delay_seconds=3,
        playwright_headless=True,
    )
    try:
        await try_collector("Amazon", AmazonCollector(settings), "iPhone 15")
        await try_collector("Flipkart", FlipkartCollector(settings), "iPhone 15")
    finally:
        await PlaywrightManager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
