"""ProductMatcher — the multi-stage "is this the same product?" pipeline.

    Stage 1: exact identifiers (GTIN/EAN/UPC/MPN/SKU/ASIN)   -> instant MATCH
    Stage 2: structured attributes (brand/storage/color/RAM)  -> hard NO_MATCH gate
    Stage 3: fuzzy string matching (RapidFuzz)                 -> similarity signal
    Stage 4: semantic embeddings (sentence-transformers)       -> similarity signal

Stage 2 only ever *rules out* a match (both sides have the attribute and it
disagrees) — it never confirms one by itself, since two different products
can share a brand/storage/color. Stages 3+4 combine into the final score,
boosted a little per agreeing attribute, then classified against the
configurable thresholds into MATCH / POSSIBLE_MATCH / NEEDS_REVIEW / NO_MATCH.

`group()` clusters a batch of listings (a search result set) into common
product groups using only high-confidence MATCH edges — POSSIBLE_MATCH and
NEEDS_REVIEW listings are surfaced but never auto-merged, per the brief.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.config import Settings, get_settings
from app.database.models import MatchStatus
from app.matching.embeddings import EmbeddingService, build_embedding_text
from app.matching.normalizer import NormalizedProduct, ProductNormalizer
from app.matching.similarity import cosine_similarity, fuzzy_ratio
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _last_digit_run(text: str | None) -> str | None:
    if not text:
        return None
    runs = re.findall(r"\d+", text)
    return runs[-1] if runs else None

# Identifier keys checked in Stage 1, in priority order.
_IDENTIFIER_KEYS = ("gtin", "ean", "upc", "mpn", "model_number", "asin", "pid", "sku")

# Stage 3/4 blend weights (must sum to 1.0 when both are available).
_FUZZY_WEIGHT = 0.45
_EMBEDDING_WEIGHT = 0.55

# Small additive bonus per agreeing structured attribute, applied after the
# fuzzy/embedding blend and capped so the total never exceeds 1.0.
_ATTRIBUTE_BONUS = {"brand": 0.03, "storage": 0.03, "color": 0.02, "ram": 0.02, "size": 0.02}


@dataclass
class MatchCandidate:
    """One listing's title + optional identifiers/specs, as the matcher
    needs them. `key` is only used by `group()` to label the result."""

    title: str
    key: str = ""
    identifiers: dict[str, str] = field(default_factory=dict)
    specifications: dict[str, str] = field(default_factory=dict)
    canonical_name: str | None = None


@dataclass
class MatchResult:
    score: float
    status: MatchStatus
    reasons: list[str]
    fuzzy_score: float
    embedding_score: float | None


@dataclass
class MatchGroup:
    members: list[str]
    pairwise_results: dict[tuple[str, str], MatchResult]  # intra-group pairs only


@dataclass
class GroupingResult:
    groups: list[MatchGroup]
    # Every pair compared, including across groups — POSSIBLE_MATCH/
    # NEEDS_REVIEW pairs live here even though they were deliberately *not*
    # merged, so a caller can still surface them for manual review.
    pairwise_results: dict[tuple[str, str], MatchResult]

    def needs_review(self) -> list[tuple[tuple[str, str], MatchResult]]:
        return [
            (pair, result)
            for pair, result in self.pairwise_results.items()
            if result.status in (MatchStatus.POSSIBLE_MATCH, MatchStatus.NEEDS_REVIEW)
        ]


@dataclass
class _Prepared:
    candidate: MatchCandidate
    normalized: NormalizedProduct
    embedding_text: str
    embedding: list[float] | None = None


class ProductMatcher:
    def __init__(
        self,
        settings: Settings | None = None,
        embedding_service: EmbeddingService | None = None,
        use_embeddings: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        self.normalizer = ProductNormalizer()
        self._embedding_service = embedding_service
        self.use_embeddings = use_embeddings

    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService.get_instance()
        return self._embedding_service

    # ── Public API ────────────────────────────────────────────────────
    def match(self, a: MatchCandidate, b: MatchCandidate) -> MatchResult:
        prepared_a = self._prepare(a)
        prepared_b = self._prepare(b)
        if self.use_embeddings:
            self._embed([prepared_a, prepared_b])
        return self._match_prepared(prepared_a, prepared_b)

    def group(self, candidates: list[MatchCandidate]) -> GroupingResult:
        """Clusters listings into common-product groups. Only `MATCH`-status
        pairs are merged; `POSSIBLE_MATCH`/`NEEDS_REVIEW` are reported in
        `pairwise_results` for manual review but kept as separate groups."""
        prepared = [self._prepare(c) for c in candidates]
        if self.use_embeddings:
            self._embed(prepared)

        parent = {c.key: c.key for c in candidates}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        pairwise: dict[tuple[str, str], MatchResult] = {}
        for i in range(len(prepared)):
            for j in range(i + 1, len(prepared)):
                pa, pb = prepared[i], prepared[j]
                result = self._match_prepared(pa, pb)
                pairwise[(pa.candidate.key, pb.candidate.key)] = result
                if result.status == MatchStatus.MATCH:
                    union(pa.candidate.key, pb.candidate.key)

        clusters: dict[str, list[str]] = {}
        for c in candidates:
            clusters.setdefault(find(c.key), []).append(c.key)

        groups = []
        for members in clusters.values():
            member_set = set(members)
            group_pairs = {k: v for k, v in pairwise.items() if k[0] in member_set and k[1] in member_set}
            groups.append(MatchGroup(members=members, pairwise_results=group_pairs))
        return GroupingResult(groups=groups, pairwise_results=pairwise)

    # ── Internals ────────────────────────────────────────────────────
    def _prepare(self, candidate: MatchCandidate) -> _Prepared:
        normalized = self.normalizer.normalize(candidate.title)
        text = build_embedding_text(
            normalized.brand, normalized.model,
            candidate.canonical_name or normalized.normalized_title,
            candidate.specifications,
        )
        return _Prepared(candidate=candidate, normalized=normalized, embedding_text=text)

    def _embed(self, prepared: list[_Prepared]) -> None:
        try:
            vectors = self.embedding_service.encode_many([p.embedding_text for p in prepared])
        except Exception:  # model unavailable/failed to load — degrade gracefully
            logger.exception("Embedding model unavailable; falling back to fuzzy-only matching.")
            self.use_embeddings = False
            return
        for p, v in zip(prepared, vectors):
            p.embedding = v

    def _match_prepared(self, a: _Prepared, b: _Prepared) -> MatchResult:
        # Stage 1: exact identifiers.
        shared_key = self._shared_identifier(a.candidate.identifiers, b.candidate.identifiers)
        if shared_key:
            return MatchResult(
                score=1.0, status=MatchStatus.MATCH,
                reasons=[f"exact identifier match ({shared_key})"],
                fuzzy_score=1.0, embedding_score=None,
            )

        # Stage 2: structured-attribute hard gate.
        mismatch = self._hard_mismatch(a.normalized, b.normalized)
        if mismatch:
            return MatchResult(score=0.0, status=MatchStatus.NO_MATCH, reasons=[mismatch], fuzzy_score=0.0, embedding_score=None)

        # Stage 3: fuzzy title similarity.
        fuzzy_score = fuzzy_ratio(a.normalized.normalized_title, b.normalized.normalized_title)

        # Stage 4: semantic embedding similarity (if available).
        embedding_score = None
        if self.use_embeddings and a.embedding and b.embedding:
            embedding_score = cosine_similarity(a.embedding, b.embedding)

        base = (
            _FUZZY_WEIGHT * fuzzy_score + _EMBEDDING_WEIGHT * embedding_score
            if embedding_score is not None
            else fuzzy_score
        )

        reasons: list[str] = []
        bonus = 0.0
        attributes_compared = 0
        na, nb = a.normalized, b.normalized

        if na.brand and nb.brand and na.brand.lower() == nb.brand.lower():
            reasons.append("same brand")
            bonus += _ATTRIBUTE_BONUS["brand"]
        if na.brand and nb.brand:
            attributes_compared += 1

        if na.storage_gb and nb.storage_gb and na.storage_gb == nb.storage_gb:
            reasons.append("same storage")
            bonus += _ATTRIBUTE_BONUS["storage"]
        if na.storage_gb and nb.storage_gb:
            attributes_compared += 1

        if na.color and nb.color and na.color.lower() == nb.color.lower():
            reasons.append("same color")
            bonus += _ATTRIBUTE_BONUS["color"]
        if na.color and nb.color:
            attributes_compared += 1

        if na.ram_gb and nb.ram_gb and na.ram_gb == nb.ram_gb:
            reasons.append("same RAM")
            bonus += _ATTRIBUTE_BONUS["ram"]
        if na.ram_gb and nb.ram_gb:
            attributes_compared += 1

        if na.size_inches and nb.size_inches and na.size_inches == nb.size_inches:
            reasons.append("same size")
            bonus += _ATTRIBUTE_BONUS["size"]
        if na.size_inches and nb.size_inches:
            attributes_compared += 1

        if fuzzy_score >= 0.85:
            reasons.append("same model")

        score = round(min(1.0, base + bonus), 4)
        status = self._classify(score, attributes_compared > 0)

        if not reasons:
            reasons.append(f"title similarity {score:.2f}")

        return MatchResult(
            score=score, status=status, reasons=reasons,
            fuzzy_score=round(fuzzy_score, 4),
            embedding_score=round(embedding_score, 4) if embedding_score is not None else None,
        )

    def _classify(self, score: float, attributes_corroborate: bool) -> MatchStatus:
        if score >= self.settings.match_threshold_match:
            return MatchStatus.MATCH
        if score >= self.settings.match_threshold_possible:
            # A borderline score with no structured attribute agreement to
            # back it up is genuinely ambiguous — flag for human review
            # instead of auto-labeling it a possible match.
            return MatchStatus.POSSIBLE_MATCH if attributes_corroborate else MatchStatus.NEEDS_REVIEW
        return MatchStatus.NO_MATCH

    @staticmethod
    def _shared_identifier(a: dict[str, str], b: dict[str, str]) -> str | None:
        for key in _IDENTIFIER_KEYS:
            va, vb = a.get(key), b.get(key)
            if va and vb and str(va).strip().lower() == str(vb).strip().lower():
                return key
        return None

    @staticmethod
    def _hard_mismatch(a: NormalizedProduct, b: NormalizedProduct) -> str | None:
        if a.brand and b.brand and a.brand.lower() != b.brand.lower():
            return f"different brand ({a.brand} vs {b.brand})"
        if a.storage_gb and b.storage_gb and a.storage_gb != b.storage_gb:
            return f"different storage ({a.storage_gb:g}GB vs {b.storage_gb:g}GB)"
        if a.color and b.color and a.color.lower() != b.color.lower():
            return f"different color ({a.color} vs {b.color})"
        if a.ram_gb and b.ram_gb and a.ram_gb != b.ram_gb:
            return f"different RAM ({a.ram_gb:g}GB vs {b.ram_gb:g}GB)"
        if a.size_inches and b.size_inches and a.size_inches != b.size_inches:
            return f"different size ({a.size_inches:g}\" vs {b.size_inches:g}\")"

        # Model numbers that are textually almost identical but end in a
        # different digit sequence are very likely different SKUs/
        # generations (WH-1000XM5 vs WH-1000XM4, iPhone 15 vs iPhone 16) —
        # fuzzy/embedding similarity alone would score these too high.
        digits_a, digits_b = _last_digit_run(a.model), _last_digit_run(b.model)
        if digits_a and digits_b and digits_a != digits_b:
            return f"different model number ({a.model} vs {b.model})"
        return None
