"""Turns a raw list of (key, value) rows scraped from a spec table into a
clean dict, reusing ProductNormalizer's unit-spacing cleanup so "8 GB" and
"8GB" don't end up as different-looking values across retailers."""
from __future__ import annotations

import re

from app.matching.normalizer import ProductNormalizer

_normalizer = ProductNormalizer()

# Some retailers' "spec" tables embed a ratings-widget row (e.g. Amazon's
# "Customer Reviews" row carries an inline star-rating script alongside its
# visible text) whose innerText leaks JS source rather than a real spec
# value — caught live while testing (see README's Live collector status).
# Recognizable by JS call-syntax that never appears in genuine spec text.
_LOOKS_LIKE_CODE_RE = re.compile(r"\.execute\(|function\s*\(|\.when\(['\"]")
_MAX_REASONABLE_SPEC_VALUE_LENGTH = 300


def parse_specification_table(rows: list[tuple[str | None, str | None]]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for raw_key, raw_value in rows:
        key = (raw_key or "").strip().rstrip(":")
        value = (raw_value or "").strip()
        if not key or not value:
            continue
        if len(value) > _MAX_REASONABLE_SPEC_VALUE_LENGTH or _LOOKS_LIKE_CODE_RE.search(value):
            continue
        specs[key] = value
    return _normalizer.normalize_specifications(specs)
