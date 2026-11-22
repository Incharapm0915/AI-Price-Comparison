"""Pure text->value parsing for ratings/reviews."""
from __future__ import annotations

import re
from datetime import datetime

_RATING_OUT_OF_5_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:out of|/)\s*5", re.IGNORECASE)
_HELPFUL_RE = re.compile(r"([\d,]+)\s*(?:people|person)?\s*found this helpful", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")


def parse_rating_text(text: str | None) -> float | None:
    """"4.5 out of 5 stars" / "4.5/5" / "4.5" -> 4.5."""
    if not text:
        return None
    match = _RATING_OUT_OF_5_RE.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    try:
        return float(text.strip())
    except ValueError:
        return None


def parse_helpful_count(text: str | None) -> int | None:
    """"23 people found this helpful" -> 23."""
    if not text:
        return None
    match = _HELPFUL_RE.search(text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_review_date(text: str | None) -> datetime | None:
    """"Reviewed in India on 12 March 2024" -> datetime(2024, 3, 12).
    Returns None (never a guessed date) if no recognizable date is found."""
    if not text:
        return None
    match = _DATE_RE.search(text)
    if not match:
        return None
    day, month_name, year = match.groups()
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(f"{day} {month_name} {year}", fmt)
        except ValueError:
            continue
    return None


def parse_verified_purchase(text: str | None) -> bool | None:
    if not text:
        return None
    return "verified purchase" in text.lower()
