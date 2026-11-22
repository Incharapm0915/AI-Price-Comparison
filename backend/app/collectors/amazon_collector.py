"""Live Amazon (amazon.in) collector — Playwright-driven, read-only, public
pages only. No login, no cart, no checkout.

robots.txt for amazon.in (checked at the time this was written) allows the
plain search path (`/s?k=...`) and product detail pages (`/dp/<ASIN>`) for
a generic user agent; it specifically disallows write-actions (login,
cart, wishlist mutation, "write a review") and a handful of filtered-search
URL shapes this collector never constructs. `is_allowed()` (Phase 6) is
still checked on every request regardless — this comment is not a
substitute for that check, just context for why these particular paths
were chosen.

Selectors below target Amazon's long-stable search/product page structure
(the same structure visible to any signed-out browser). If Amazon changes
their markup, `parse_search_results`/`parse_product`/`parse_reviews` are
the only things that need updating — the retry/throttle/block-detection
machinery in `PlaywrightCollector` does not change.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from playwright.async_api import Page

from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.types import CollectedListingSummary, CollectedProduct, CollectedReview
from app.parsers.price_parser import compute_discount_percent, parse_discount_percent, parse_price
from app.parsers.product_parser import parse_availability
from app.parsers.review_parser import (
    parse_helpful_count,
    parse_rating_text,
    parse_review_date,
    parse_verified_purchase,
)
from app.parsers.seller_parser import parse_seller_name
from app.parsers.specification_parser import parse_specification_table
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AmazonCollector(PlaywrightCollector):
    retailer = "amazon"
    base_url = "https://www.amazon.in"
    search_result_selector = 'div[data-component-type="s-search-result"]'
    product_detail_selector = "#productTitle"
    reviews_wait_selector = 'div[data-hook="review"], #cm-cr-dp-review-list, div[data-hook="reviews-medley-widget"]'
    navigation_timeout_ms = 20000

    def build_search_url(self, query: str) -> str:
        return f"{self.base_url}/s?k={quote_plus(query)}"

    def build_reviews_url(self, product_url: str) -> str:
        asin = self._extract_asin(product_url)
        return f"{self.base_url}/product-reviews/{asin}" if asin else product_url

    def additional_block_indicators(self) -> list[str]:
        return [
            "sorry, we just need to make sure you're not a robot",
            "type the characters you see in this image",
            "to discuss automated access to amazon data",
        ]

    # ── parsing hooks ────────────────────────────────────────────────
    async def parse_search_results(self, page: Page) -> list[CollectedListingSummary]:
        cards = await page.locator(self.search_result_selector).all()
        results: list[CollectedListingSummary] = []

        for card in cards:
            asin = await card.get_attribute("data-asin")
            if not asin:
                continue

            # Amazon nests the visible title text inside several spans
            # under the <h2> (some of them brand-only fragments) — take the
            # <h2>'s full inner_text so nothing gets truncated to just the
            # first nested span's text.
            title = await self._first_text(card, "h2")
            if not title:
                continue

            price = None
            price_locator = card.locator("span.a-price > span.a-offscreen")
            if await price_locator.count():
                price = parse_price(await price_locator.first.inner_text())

            rating = None
            rating_text = await self._first_text(card, "span.a-icon-alt")
            if rating_text:
                rating = parse_rating_text(rating_text)

            rating_count = None
            count_text = await self._first_text(card, 'span[aria-label][dir="auto"]')
            if count_text:
                digits = "".join(c for c in count_text if c.isdigit())
                rating_count = int(digits) if digits else None

            image_locator = card.locator("img.s-image")
            image_url = await image_locator.first.get_attribute("src") if await image_locator.count() else None

            results.append(
                CollectedListingSummary(
                    retailer=self.retailer,
                    retailer_product_id=asin,
                    product_name=title.strip(),
                    product_url=f"{self.base_url}/dp/{asin}",
                    price=price,
                    rating=rating,
                    rating_count=rating_count,
                    image_url=image_url,
                )
            )
        return results

    async def parse_product(self, page: Page) -> CollectedProduct:
        url = page.url
        asin = self._extract_asin(url) or ""

        title = (await self._first_text(page, "#productTitle") or "").strip()

        price = None
        for selector in ("span.a-price > span.a-offscreen", "#priceblock_ourprice", "#priceblock_dealprice"):
            text = await self._first_text(page, selector)
            if text:
                price = parse_price(text)
                if price:
                    break

        mrp_text = await self._first_text(page, ".basisPrice span.a-offscreen, #priceblock_ourprice ~ .a-text-strike")
        mrp = parse_price(mrp_text)

        discount_text = await self._first_text(page, ".savingsPercentage")
        discount_percent = parse_discount_percent(discount_text) or compute_discount_percent(price, mrp)

        rating_text = await self._first_text(page, "#acrPopover span.a-icon-alt, span.a-icon-alt")
        rating = parse_rating_text(rating_text)

        rating_count = None
        count_text = await self._first_text(page, "#acrCustomerReviewText")
        if count_text:
            digits = "".join(c for c in count_text if c.isdigit())
            rating_count = int(digits) if digits else None

        availability_text = await self._first_text(page, "#availability span, #availability")
        availability = parse_availability(availability_text)

        description = await self._first_text(page, "#productDescription")
        highlights = await self._all_texts(page, "#feature-bullets li span.a-list-item")

        spec_rows = await self._spec_table_rows(page)
        specifications = parse_specification_table(spec_rows)

        image_urls = await self._image_urls(page)

        seller_text = await self._first_text(page, "#sellerProfileTriggerId, #merchant-info")
        seller_name = parse_seller_name(seller_text)

        return CollectedProduct(
            retailer=self.retailer,
            retailer_product_id=asin,
            product_name=title,
            product_url=url,
            description=description,
            highlights=highlights,
            specifications=specifications,
            image_urls=image_urls,
            price=price,
            mrp=mrp,
            discount_percent=discount_percent,
            currency="INR",
            availability=availability,
            rating=rating,
            rating_count=rating_count,
            review_count=rating_count,  # Amazon doesn't separate these on the product page
            seller_name=seller_name,
            identifiers={"asin": asin} if asin else {},
        )

    async def parse_reviews(self, page: Page) -> list[CollectedReview]:
        cards = await page.locator('div[data-hook="review"]').all()
        reviews: list[CollectedReview] = []

        for card in cards:
            review_id = await card.get_attribute("id")
            reviewer_name = await self._first_text(card, ".a-profile-name")
            rating_text = await self._first_text(card, 'i[data-hook="review-star-rating"] span, i[data-hook="cmps-review-star-rating"] span')
            title = await self._first_text(card, 'a[data-hook="review-title"] span, span[data-hook="review-title"]')
            body = await self._first_text(card, 'span[data-hook="review-body"] span, span[data-hook="review-body"]')
            date_text = await self._first_text(card, 'span[data-hook="review-date"]')
            verified_text = await self._first_text(card, 'span[data-hook="avp-badge"]')
            helpful_text = await self._first_text(card, 'span[data-hook="helpful-vote-statement"]')

            reviews.append(
                CollectedReview(
                    external_review_id=review_id,
                    reviewer_name=reviewer_name,
                    rating=parse_rating_text(rating_text),
                    review_title=title,
                    review_text=body,
                    review_date=parse_review_date(date_text),
                    verified_purchase=parse_verified_purchase(verified_text) or False,
                    helpful_count=parse_helpful_count(helpful_text),
                )
            )
        return reviews

    # ── small DOM helpers (defensive: missing element -> None, never raises) ──
    @staticmethod
    async def _first_text(locator_root, selector: str) -> str | None:
        locator = locator_root.locator(selector)
        if await locator.count() == 0:
            return None
        try:
            return await locator.first.inner_text()
        except Exception:
            return None

    @staticmethod
    async def _all_texts(locator_root, selector: str) -> list[str]:
        locator = locator_root.locator(selector)
        count = await locator.count()
        texts = []
        for i in range(count):
            try:
                text = await locator.nth(i).inner_text()
            except Exception:
                continue
            if text and text.strip():
                texts.append(text.strip())
        return texts

    @staticmethod
    async def _spec_table_rows(page: Page) -> list[tuple[str | None, str | None]]:
        rows = []
        for table_selector in ("#productDetails_techSpec_section_1 tr", "table.prodDetTable tr"):
            row_locator = page.locator(table_selector)
            count = await row_locator.count()
            for i in range(count):
                row = row_locator.nth(i)
                try:
                    key = await row.locator("th").first.inner_text()
                    value = await row.locator("td").first.inner_text()
                except Exception:
                    continue
                rows.append((key, value))
            if rows:
                break
        return rows

    @staticmethod
    async def _image_urls(page: Page) -> list[str]:
        urls: list[str] = []
        main_image = page.locator("#landingImage, #imgBlkFront")
        if await main_image.count():
            src = await main_image.first.get_attribute("src")
            if src:
                urls.append(src)
        thumbs = page.locator("#altImages img")
        count = await thumbs.count()
        for i in range(count):
            src = await thumbs.nth(i).get_attribute("src")
            if src and src not in urls:
                urls.append(src)
        return urls

    @staticmethod
    def _extract_asin(url: str) -> str | None:
        for marker in ("/dp/", "/gp/product/", "/product-reviews/"):
            if marker in url:
                tail = url.split(marker, 1)[1]
                return tail.split("/")[0].split("?")[0]
        return None
