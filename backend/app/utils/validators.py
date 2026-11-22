"""Small, dependency-free validators reused across collectors and parsers."""
from urllib.parse import urlparse


def is_valid_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_valid_price(value: float | None) -> bool:
    return value is not None and value > 0


def is_non_empty(value: str | None) -> bool:
    return bool(value and value.strip())
