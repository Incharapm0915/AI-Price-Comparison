"""Live Flipkart (flipkart.com) collector — Playwright-driven, read-only,
public pages only. No login, no cart, no checkout.

Two things worth being upfront about, discovered while building this:

1. Flipkart's class names are short, auto-generated, and churn across
   deploys (e.g. `_4rR01T`, `_30jeq3`) — unlike Amazon's long-stable
   `data-component-type`/`id`-based structure. The selectors below match
   Flipkart's markup as observed while building this adapter; they are the
   single most likely thing to need updating if this stops working, and
   that's expected maintenance, not a bug in the collection framework.
2. Flipkart fronts flipkart.com with reCAPTCHA Enterprise that can trigger
   even on a plain, unauthenticated page load with no unusual traffic
   pattern (observed directly while developing this adapter). Per this
   project's data collection policy, that CAPTCHA is never solved or
   bypassed — `additional_block_indicators()` below detects Flipkart's
   specific "Are you a human?" interstitial so `PlaywrightCollector` raises
   `CollectorAccessDeniedError` and stops immediately rather than retrying
   into it or attempting to work around it.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from playwright.async_api import Page

from app.collectors.playwright_collector import PlaywrightCollector
from app.collectors.types import CollectedListingSummary, CollectedProduct, CollectedReview
from app.parsers.price_parser import parse_price
from app.parsers.review_parser import parse_helpful_count, parse_rating_text, parse_review_date
from app.parsers.specification_parser import parse_specification_table
from app.utils.logging import get_logger

logger = get_logger(__name__)


class FlipkartCollector(PlaywrightCollector):
    retailer = "flipkart"
    base_url = "https://www.flipkart.com"
    search_result_selector = "div[data-id]"
    # Flipkart's product *listing* page still has semi-stable, human-named
    # classes (used above/below); the product *detail* page has migrated to
    # an atomic/hashed CSS system (class names like "v1zwn21l _1psv1zeb9")
    # that are regenerated per deploy and unusable as selectors. `h1` is the
    # one reliably stable hook there — price/rating on that page fall back
    # to text-pattern matching instead of class selectors for that reason.
    product_detail_selector = "h1"
    navigation_timeout_ms = 20000

    def build_search_url(self, query: str) -> str:
        return f"{self.base_url}/search?q={quote_plus(query)}"

    def additional_block_indicators(self) -> list[str]:
        return ["flipkart recaptcha", "are you a human", "confirming..."]

    # ── parsing hooks ────────────────────────────────────────────────
    async def parse_search_results(self, page: Page) -> list[CollectedListingSummary]:
        cards = await page.locator("div[data-id]").all()
        results: list[CollectedListingSummary] = []

        for card in cards:
            product_id = await card.get_attribute("data-id")
            if not product_id:
                continue

            title = await self._first_text(card, "div.RG5Slk")
            link = card.locator("a")
            href = await link.first.get_attribute("href") if await link.count() else None
            if not title or not href:
                continue

            price_text = await self._first_text(card, "div.hZ3P6w")
            price = parse_price(price_text)

            rating_text = await self._first_text(card, "div.MKiFS6")
            rating = parse_rating_text(rating_text)

            image_locator = card.locator("img")
            image_url = await image_locator.first.get_attribute("src") if await image_locator.count() else None

            results.append(
                CollectedListingSummary(
                    retailer=self.retailer,
                    retailer_product_id=product_id,
                    product_name=title.strip(),
                    product_url=f"{self.base_url}{href}" if href.startswith("/") else href,
                    price=price,
                    rating=rating,
                    image_url=image_url,
                )
            )
        return results

    async def parse_product(self, page: Page) -> CollectedProduct:
        url = page.url
        product_id = self._extract_pid(url) or ""

        title = (await self._first_text(page, "h1") or "").strip()

        # Price on the current detail-page markup has no stable class hook
        # (see class comment above) — match the rendered "₹<amount>" text
        # node directly instead. Scoped to *after* the <h1> in document
        # order so it lands on the buy-box price, not an unrelated ₹ price
        # from a "recommended products" carousel rendered earlier on the page.
        price = parse_price(
            await self._first_xpath_text(page, "//h1/following::*[starts-with(normalize-space(text()),'₹')][1]")
        )

        # Deliberately not scanning the full page body for "out of stock":
        # Flipkart renders every size/storage/color variant's stock state
        # on the same page (e.g. "256 GB — 1 left" next to "512 GB — Out of
        # stock"), so a body-wide text search would misreport an in-stock
        # selected variant as unavailable whenever *any* sibling variant
        # isn't. Defaulting to IN_STOCK is the more honest choice until a
        # selector scoped to just the selected variant's buy-box is found.
        availability = "IN_STOCK"

        highlights = await self._all_texts(page, "ul.HwRTzP li, div._21Ahn- li, div.xFVion li")

        spec_rows = await self._spec_table_rows(page)
        specifications = parse_specification_table(spec_rows)

        image_urls = await self._image_urls(page)

        # MRP, discount, on-page rating, and rating_count are best-effort on
        # this page (no reliable non-hashed hook found) — left None rather
        # than risk extracting the wrong number when a selector is stale.
        mrp = None
        discount_percent = None
        rating = None
        rating_count = None

        return CollectedProduct(
            retailer=self.retailer,
            retailer_product_id=product_id,
            product_name=title,
            product_url=url,
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
            review_count=rating_count,
            identifiers={"pid": product_id} if product_id else {},
        )

    async def parse_reviews(self, page: Page) -> list[CollectedReview]:
        cards = await page.locator("div._27M-vq, div.EKFha-").all()
        reviews: list[CollectedReview] = []

        for card in cards:
            rating_text = await self._first_text(card, "div._3LWZlK, div.XQDdHH")
            title = await self._first_text(card, "p._2-N8zT, p.z9E0IG")
            body = await self._first_text(card, "div.t-ZTKy, div.ZmyHeo")
            reviewer_name = await self._first_text(card, "p._2sc7ZR, p._2NsDsF")
            date_text = await self._first_text(card, "p._2sc7ZR.Rquyfr, p._2NsDsF.qytdMk")
            helpful_text = await self._first_text(card, "span._1LmwT9")

            reviews.append(
                CollectedReview(
                    reviewer_name=reviewer_name,
                    rating=parse_rating_text(rating_text),
                    review_title=title,
                    review_text=body,
                    review_date=parse_review_date(date_text),
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
    async def _first_xpath_text(page: Page, xpath: str) -> str | None:
        locator = page.locator(f"xpath={xpath}")
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
        row_locator = page.locator("tr.WJdYP6, tr._1s_Smc")
        count = await row_locator.count()
        for i in range(count):
            row = row_locator.nth(i)
            try:
                key = await row.locator("td").nth(0).inner_text()
                value = await row.locator("td").nth(1).inner_text()
            except Exception:
                continue
            rows.append((key, value))
        return rows

    @staticmethod
    async def _image_urls(page: Page) -> list[str]:
        urls: list[str] = []
        thumbs = page.locator("div._2r_T1I img, div.qOPjUY img, img._396cs4")
        count = await thumbs.count()
        for i in range(count):
            src = await thumbs.nth(i).get_attribute("src")
            if src and src not in urls:
                urls.append(src)
        return urls

    @staticmethod
    def _extract_pid(url: str) -> str | None:
        if "pid=" in url:
            return url.split("pid=", 1)[1].split("&")[0]
        return None
