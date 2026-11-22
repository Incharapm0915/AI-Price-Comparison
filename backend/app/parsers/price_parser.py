"""Pure text->value parsing for pricing. Collectors extract raw strings
from the DOM; these functions turn that raw text into numbers, so the same
logic is testable without a browser and reusable across retailers."""
from __future__ import annotations

import re

_NUMBER_RE = re.compile(r"[\d,]+(?:\.\d+)?")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def parse_price(text: str | None) -> float | None:
    """"₹49,999.00" / "Rs. 49,999" / "$699.99" -> 49999.0. None if no
    number is found (never guesses)."""
    if not text:
        return None
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_discount_percent(text: str | None) -> float | None:
    """"-18%" / "(18% off)" -> 18.0."""
    if not text:
        return None
    match = _PERCENT_RE.search(text)
    return float(match.group(1)) if match else None


def compute_discount_percent(price: float | None, mrp: float | None) -> float | None:
    """Derives a discount percentage when the page shows price+MRP but not
    an explicit discount badge. Never fabricates a discount when the
    numbers don't actually indicate one (mrp <= price)."""
    if not price or not mrp or mrp <= price:
        return None
    return round((1 - price / mrp) * 100, 2)
