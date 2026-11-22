"""Owns the process-wide Playwright + Browser instance. Collectors borrow
short-lived `BrowserContext`s from it rather than each launching their own
browser (expensive) or sharing one context across requests (unsafe — a
context accumulates cookies/storage)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PlaywrightManager:
    _playwright: Playwright | None = None
    _browser: Browser | None = None

    @classmethod
    async def get_browser(cls) -> Browser:
        settings = get_settings()
        if cls._browser is None or not cls._browser.is_connected():
            if cls._playwright is None:
                cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(headless=settings.playwright_headless)
            logger.info("Playwright Chromium launched (headless=%s)", settings.playwright_headless)
        return cls._browser

    @classmethod
    @asynccontextmanager
    async def new_context(cls, **kwargs):
        browser = await cls.get_browser()
        context: BrowserContext = await browser.new_context(**kwargs)
        try:
            yield context
        finally:
            await context.close()

    @classmethod
    async def shutdown(cls) -> None:
        if cls._browser is not None:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright is not None:
            await cls._playwright.stop()
            cls._playwright = None
