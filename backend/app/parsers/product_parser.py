"""Pure text->value parsing shared across retailer product pages —
availability text in particular varies a lot in wording but maps to the
same small set of states."""
from __future__ import annotations


def parse_availability(text: str | None) -> str:
    """Free-text availability copy -> one of IN_STOCK / OUT_OF_STOCK /
    UNAVAILABLE / UNKNOWN. Defaults to UNKNOWN rather than guessing."""
    if not text:
        return "UNKNOWN"
    t = text.lower()
    if "currently unavailable" in t or "unavailable" in t:
        return "UNAVAILABLE"
    if "out of stock" in t or "sold out" in t:
        return "OUT_OF_STOCK"
    if "in stock" in t or "left in stock" in t or "available" in t:
        return "IN_STOCK"
    return "UNKNOWN"
