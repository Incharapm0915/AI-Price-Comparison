"""Pure text->value parsing for seller info."""
from __future__ import annotations

from app.parsers.review_parser import parse_rating_text

_SELLER_PREFIXES = ("sold by ", "seller: ", "sold by:")


def parse_seller_name(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    lower = cleaned.lower()
    for prefix in _SELLER_PREFIXES:
        if lower.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    cleaned = cleaned.strip()
    return cleaned or None


def parse_seller_rating(text: str | None) -> float | None:
    return parse_rating_text(text)
