"""ProductNormalizer — turns a raw, retailer-worded title into structured
attributes (brand, model, RAM, storage, color) plus a cleaned string for
fuzzy/embedding comparison.

    "Samsung Galaxy S24 (Black, 256 GB)"
    -> brand=Samsung, model="Galaxy S24", storage_gb=256, color=Black

    "SAMSUNG Galaxy S24 5G AI Smartphone 8GB 256GB Black"
    -> brand=Samsung, model="Galaxy S24", ram_gb=8, storage_gb=256, color=Black

This is intentionally heuristic, not a full NLP pipeline — it only needs to
get brand/model/RAM/storage/color close enough that Stage 2 (attribute
comparison), Stage 3 (fuzzy), and Stage 4 (embeddings) of the matcher
(Phase 5) can do the rest.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Canonical brand name <- every raw spelling/casing/alias a title might use.
# Keys are matched case-insensitively; longest alias wins so "One Plus"
# doesn't get shadowed by a shorter partial alias.
BRAND_ALIASES: dict[str, str] = {
    "samsung": "Samsung",
    "apple": "Apple",
    "oneplus": "OnePlus",
    "one plus": "OnePlus",
    "dell": "Dell",
    "sony": "Sony",
    "boat": "boAt",
    "lg": "LG",
    "xiaomi": "Xiaomi",
    "mi": "Xiaomi",
    "redmi": "Xiaomi",
    "amazon": "Amazon",
    "marq": "MarQ",
    "hp": "HP",
    "lenovo": "Lenovo",
    "asus": "Asus",
    "google": "Google",
    "realme": "realme",
    "vivo": "vivo",
    "oppo": "OPPO",
    "nothing": "Nothing",
    "jbl": "JBL",
    "bose": "Bose",
}
# Sorted longest-alias-first so multi-word aliases match before their
# single-word substrings do.
_BRAND_LOOKUP = sorted(BRAND_ALIASES.items(), key=lambda kv: -len(kv[0]))

# Multi-word colors must be listed before any single-word color they contain
# (e.g. "Space Gray" before "Gray") — extraction always tries longest first.
COLOR_WORDS: list[str] = [
    "glacier white", "cool blue", "iron gray", "aurora purple", "platinum silver",
    "midnight black", "space gray", "space grey", "rose gold", "sky blue",
    "ocean blue", "matte black",
    "midnight", "starlight", "charcoal", "titanium", "graphite",
    "black", "white", "blue", "red", "green", "yellow", "purple", "violet",
    "pink", "gray", "grey", "silver", "gold", "orange", "brown", "navy",
    "teal", "beige", "cream", "coral", "bronze", "copper",
]
_COLOR_LOOKUP = sorted(set(COLOR_WORDS), key=len, reverse=True)

# Pure marketing/category noise — safe to strip because none of this
# catalog's real model names contain these tokens.
_NOISE_PHRASES = [
    "5g ai smartphone", "5g", "4g", "lte", "ai smartphone", "smartphone",
    "smart phone", "wireless headphones", "bluetooth headset", "bluetooth headphones",
    "headphones", "headset", "mobile phone", "cellphone", "laptop",
]
_NOISE_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in sorted(_NOISE_PHRASES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(TB|GB|MB)\b", re.IGNORECASE)
_SCREEN_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:inch(?:es)?|\")", re.IGNORECASE)
_UNIT_SPACING_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s+(GB|TB|MB|MP|MAH|MHZ|GHZ|HZ|W|INCH|INCHES|\")", re.IGNORECASE
)
_PUNCT_RE = re.compile(r"[\(\)\[\]{},/|_\-]+")
_WS_RE = re.compile(r"\s+")


@dataclass
class NormalizedProduct:
    raw_title: str
    normalized_title: str
    brand: str | None = None
    model: str | None = None
    storage_gb: float | None = None
    ram_gb: float | None = None
    color: str | None = None
    size_inches: float | None = None
    tokens: frozenset[str] = field(default_factory=frozenset)


def _to_gb(value: float, unit: str) -> float:
    unit = unit.upper()
    if unit == "TB":
        return value * 1024
    if unit == "MB":
        return value / 1024
    return value


class ProductNormalizer:
    """Stateless — every method is a pure function of its input, so a
    single shared instance (or none at all; these could be module
    functions) is safe to reuse across requests/collectors."""

    def normalize(self, title: str) -> NormalizedProduct:
        raw_title = title
        text = self._clean_unicode_and_whitespace(title)

        brand, text = self._extract_brand(text)
        ram_gb, storage_gb, text = self._extract_sizes(text)
        size_inches, text = self._extract_screen_size(text)
        color, text = self._extract_color(text)
        model = self._extract_model(text)

        normalized_title_parts = [p for p in [brand, model, color] if p]
        normalized_title = " ".join(normalized_title_parts).lower().strip()
        if not normalized_title:
            normalized_title = self._clean_unicode_and_whitespace(title).lower()

        tokens = frozenset(t for t in normalized_title.split() if t)

        return NormalizedProduct(
            raw_title=raw_title,
            normalized_title=normalized_title,
            brand=brand,
            model=model,
            storage_gb=storage_gb,
            ram_gb=ram_gb,
            color=color,
            size_inches=size_inches,
            tokens=tokens,
        )

    def normalize_specifications(self, specifications: dict) -> dict:
        """Cleans whitespace/unit-spacing in spec values (e.g. "8 GB" ->
        "8GB") without renaming or dropping arbitrary retailer-specific keys."""
        cleaned: dict = {}
        for key, value in (specifications or {}).items():
            if isinstance(value, str):
                v = self._clean_unicode_and_whitespace(value)
                v = _UNIT_SPACING_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}", v)
                cleaned[key] = v
            else:
                cleaned[key] = value
        return cleaned

    @staticmethod
    def build_common_product_id(brand: str | None, model: str | None, storage_gb: float | None, color: str | None) -> str:
        """e.g. ("Apple", "iPhone 15", 128, "Black") -> "APPLE_IPHONE_15_128_BLACK"."""
        parts = [brand or "", model or ""]
        if storage_gb:
            parts.append(f"{int(storage_gb)}" if storage_gb == int(storage_gb) else str(storage_gb))
        if color:
            parts.append(color)
        slug = "_".join(parts)
        slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_").upper()
        slug = re.sub(r"_+", "_", slug)
        return slug or "UNKNOWN_PRODUCT"

    # ── internal steps ───────────────────────────────────────────────
    def _clean_unicode_and_whitespace(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("’", "'").replace("–", "-").replace("—", "-")
        text = _WS_RE.sub(" ", text).strip()
        return text

    def _extract_brand(self, text: str) -> tuple[str | None, str]:
        lower = text.lower()
        for alias, canonical in _BRAND_LOOKUP:
            pattern = r"\b" + re.escape(alias) + r"\b"
            match = re.search(pattern, lower)
            if match:
                start, end = match.span()
                remaining = text[:start] + " " + text[end:]
                return canonical, self._collapse(remaining)
        return None, text

    def _extract_sizes(self, text: str) -> tuple[float | None, float | None, str]:
        matches = list(_SIZE_RE.finditer(text))
        if not matches:
            return None, None, text

        parsed = []
        for m in matches:
            value = float(m.group(1))
            unit = m.group(2).upper()
            # Only the word immediately following (allowing a little
            # punctuation/whitespace) counts — otherwise "128 GB) 8 GB RAM"
            # would misattribute RAM to the storage figure too.
            tail = text[m.end(): m.end() + 8]
            is_ram = bool(re.match(r"[\s,)]*RAM\b", tail, re.IGNORECASE))
            parsed.append({"gb": _to_gb(value, unit), "is_ram": is_ram, "span": m.span()})

        # Remove every matched "<num><unit>" occurrence (and a trailing
        # standalone "RAM" word right after it, if present) from the text.
        cleaned = text
        for m in sorted(matches, key=lambda mm: mm.start(), reverse=True):
            end = m.end()
            trailing = cleaned[end:end + 8]
            ram_word = re.match(r"[\s,)]*RAM\b", trailing, re.IGNORECASE)
            extra = ram_word.end() if ram_word else 0
            cleaned = cleaned[: m.start()] + " " + cleaned[end + extra:]
        cleaned = self._collapse(cleaned)

        ram_gb = next((p["gb"] for p in parsed if p["is_ram"]), None)
        storage_candidates = [p["gb"] for p in parsed if not p["is_ram"]]

        if ram_gb is None and len(storage_candidates) >= 2:
            # No explicit "RAM" label anywhere (e.g. "8GB 256GB Black") —
            # convention: the smaller figure is RAM, the larger is storage.
            storage_candidates.sort()
            ram_gb = storage_candidates[0]
            storage_candidates = storage_candidates[1:]

        storage_gb = max(storage_candidates) if storage_candidates else None
        return ram_gb, storage_gb, cleaned

    def _extract_screen_size(self, text: str) -> tuple[float | None, str]:
        match = _SCREEN_SIZE_RE.search(text)
        if not match:
            return None, text
        size = float(match.group(1))
        start, end = match.span()
        remaining = self._collapse(text[:start] + " " + text[end:])
        return size, remaining

    def _extract_color(self, text: str) -> tuple[str | None, str]:
        lower = text.lower()
        for color in _COLOR_LOOKUP:
            pattern = r"\b" + re.escape(color) + r"\b"
            match = re.search(pattern, lower)
            if match:
                start, end = match.span()
                remaining = text[:start] + " " + text[end:]
                return color.title(), self._collapse(remaining)
        return None, text

    def _extract_model(self, text: str) -> str | None:
        text = _NOISE_RE.sub(" ", text)
        text = _PUNCT_RE.sub(" ", text)
        text = self._collapse(text)
        return text or None

    def _collapse(self, text: str) -> str:
        text = _PUNCT_RE.sub(" ", text)
        return _WS_RE.sub(" ", text).strip()
