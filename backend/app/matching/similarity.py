"""Similarity primitives shared by the matcher: RapidFuzz string similarity
and cosine similarity for embedding vectors."""
from __future__ import annotations

import math

from rapidfuzz import fuzz


def fuzzy_ratio(a: str, b: str) -> float:
    """Token-set ratio (order/duplicate-word insensitive), 0.0-1.0.
    Good for "Sony WH-1000XM5 Wireless Headphones Black" vs
    "Sony WH1000XM5 Bluetooth Headset (Black)" style differences."""
    if not a or not b:
        return 0.0
    return fuzz.token_set_ratio(a, b) / 100.0


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Returns 0.0-1.0 (negative cosine similarity is clamped to 0 — two
    embeddings pointing in genuinely opposite directions are not "a little
    bit similar", they're unrelated for our purposes)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))
