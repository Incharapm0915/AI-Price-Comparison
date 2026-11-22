"""robots.txt enforcement. Every URL a live collector wants to fetch must
pass `is_allowed()` first — this is not optional per the project's data
collection policy."""
from __future__ import annotations

import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 3600
_cache: dict[str, tuple[RobotFileParser, float]] = {}


def clear_cache() -> None:
    _cache.clear()


def _get_parser(url: str) -> RobotFileParser:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    cached = _cache.get(origin)
    if cached and time.monotonic() - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    parser = RobotFileParser()
    robots_url = f"{origin}/robots.txt"
    try:
        response = httpx.get(robots_url, timeout=10, follow_redirects=True)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # No robots.txt published -> nothing to disallow.
            parser.parse([])
            logger.debug("robots.txt at %s -> HTTP %s; treating as allow-all", robots_url, response.status_code)
    except httpx.HTTPError as exc:
        logger.warning("Could not fetch %s (%s); treating as allow-all", robots_url, exc)
        parser.parse([])

    _cache[origin] = (parser, time.monotonic())
    return parser


def is_allowed(url: str, user_agent: str = "*") -> bool:
    """True if `user_agent` may fetch `url` per that origin's robots.txt."""
    try:
        return _get_parser(url).can_fetch(user_agent, url)
    except Exception:
        logger.exception("robots.txt check failed for %s; failing closed (disallow)", url)
        return False
