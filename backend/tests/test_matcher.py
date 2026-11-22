"""Phase 5 tests for ProductMatcher — 20+ Amazon-vs-Flipkart matching
examples per the brief's TESTING section, run with embeddings enabled
(the real sentence-transformers model, not a mock) since this is exactly
the code path the app relies on to solve "same product, different title".
"""
import pytest

from app.database.models import MatchStatus
from app.matching.product_matcher import MatchCandidate, ProductMatcher

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def matcher() -> ProductMatcher:
    return ProductMatcher()


def _match(matcher, title_a, title_b, **kwargs_a_b):
    a = MatchCandidate(title=title_a, **kwargs_a_b.get("a", {}))
    b = MatchCandidate(title=title_b, **kwargs_a_b.get("b", {}))
    return matcher.match(a, b)


# (amazon_title, flipkart_title, expected_status)
MATCH_CASES = [
    # 1 — brief's canonical example.
    ("Apple iPhone 15 128GB Black", "Apple iPhone 15 Black 128 GB", MatchStatus.MATCH),
    # 2 — brief's canonical NO_MATCH (different storage).
    ("iPhone 15 128GB", "iPhone 15 256GB", MatchStatus.NO_MATCH),
    # 3 — brief's canonical NO_MATCH (different storage).
    ("Samsung Galaxy S24 256GB", "Samsung Galaxy S24 128GB", MatchStatus.NO_MATCH),
    # 4 — brief's canonical MATCH (hyphen/wording difference).
    ("Sony WH-1000XM5 Black", "Sony WH1000XM5 Wireless Headphones Black", MatchStatus.MATCH),
    # 5 — the exact problem-statement example.
    (
        "Samsung Galaxy S24 5G AI Smartphone, 8GB RAM, 256GB, Black",
        "Samsung Galaxy S24 (Black, 256 GB) 8 GB RAM",
        MatchStatus.MATCH,
    ),
    # 6 — different brand entirely.
    ("Apple iPhone 15 128GB Black", "Samsung Galaxy S24 128GB Black", MatchStatus.NO_MATCH),
    # 7 — different color.
    ("Apple iPhone 15 128GB Black", "Apple iPhone 15 128GB Blue", MatchStatus.NO_MATCH),
    # 8 — different RAM variant.
    ("OnePlus 12R 8GB RAM 128GB Cool Blue", "OnePlus 12R 16GB RAM 128GB Cool Blue", MatchStatus.NO_MATCH),
    # 9 — laptop, matching storage/color, different wording/order.
    (
        "Apple MacBook Air M2 Laptop, 8GB RAM, 256GB SSD, Midnight",
        "Apple MacBook Air M2 (Midnight) - 256GB SSD 8GB RAM",
        MatchStatus.MATCH,
    ),
    # 10 — laptop, different storage.
    ("Apple MacBook Air M2 256GB SSD Starlight", "Apple MacBook Air M2 512GB SSD Starlight", MatchStatus.NO_MATCH),
    # 11 — TV, same size, close wording.
    ("Samsung 55 inch Crystal 4K UHD Smart TV", "Samsung 55 inches Crystal 4K UHD Smart TV", MatchStatus.MATCH),
    # 12 — TV, different screen size.
    ("LG 50 inch UQ7500 4K Smart TV", "LG 55 inch UQ7500 4K Smart TV", MatchStatus.NO_MATCH),
    # 13 — completely unrelated products.
    ("Sony WH-1000XM5 Wireless Headphones Black", "Samsung Galaxy S24 256GB Black", MatchStatus.NO_MATCH),
    # 14 — headphone color mismatch.
    ("boAt Rockerz 550 Black", "boAt Rockerz 550 Blue", MatchStatus.NO_MATCH),
    # 15 — smartwatch, same color, different phrasing.
    ("Apple Watch Series 9 GPS, Midnight Aluminium Case", "Apple Watch Series 9 (Midnight)", MatchStatus.MATCH),
    # 16 — smartwatch, different color.
    ("Apple Watch Series 9 (Midnight)", "Apple Watch Series 9 (Starlight)", MatchStatus.NO_MATCH),
    # 17 — Xiaomi phone, marketing vs plain wording, same variant.
    (
        "Xiaomi Redmi Note 13 Pro 5G Smartphone, 8GB RAM, 128GB, Midnight Black",
        "Xiaomi Redmi Note 13 Pro (Midnight Black, 128GB) 8GB RAM",
        MatchStatus.MATCH,
    ),
    # 18 — Xiaomi phone, different storage.
    ("Xiaomi Redmi Note 13 Pro 128GB Aurora Purple", "Xiaomi Redmi Note 13 Pro 256GB Aurora Purple", MatchStatus.NO_MATCH),
    # 19 — same brand+model, but one is a different category product entirely
    # (Watch vs Galaxy phone) — brand alone must not be enough to match.
    ("Samsung Galaxy S24 128GB Black", "Samsung Crystal 4K UHD Smart TV 55 inch", MatchStatus.NO_MATCH),
    # 20 — Dell laptop, identical variant, punctuation-only difference.
    ("Dell XPS 13 512GB SSD Platinum Silver", "Dell XPS 13 (Platinum Silver) 512GB SSD", MatchStatus.MATCH),
    # 21 — OnePlus, matching variant, heavier marketing copy on Amazon side.
    (
        "OnePlus 12R 5G Smartphone, 8GB RAM, 256GB, Iron Gray",
        "OnePlus 12R (Iron Gray, 256 GB) 8 GB RAM",
        MatchStatus.MATCH,
    ),
    # 22 — near-identical apart from a completely different model number.
    ("Sony WH-1000XM5 Black", "Sony WH-1000XM4 Black", MatchStatus.NO_MATCH),
]


@pytest.mark.parametrize("title_a,title_b,expected", MATCH_CASES, ids=[f"case_{i+1}" for i in range(len(MATCH_CASES))])
def test_matching_examples(matcher, title_a, title_b, expected):
    result = matcher.match(MatchCandidate(title=title_a), MatchCandidate(title=title_b))
    assert result.status == expected, (
        f"{title_a!r} vs {title_b!r}: expected {expected}, got {result.status} "
        f"(score={result.score}, reasons={result.reasons})"
    )


def test_exact_identifier_match_overrides_everything(matcher):
    a = MatchCandidate(title="Totally different wording A", identifiers={"asin": "B0ABC12345"})
    b = MatchCandidate(title="Completely unrelated wording B", identifiers={"asin": "b0abc12345"})
    result = matcher.match(a, b)
    assert result.status == MatchStatus.MATCH
    assert result.score == 1.0
    assert "identifier" in result.reasons[0]


def test_match_result_includes_reasons_matching_brief_example(matcher):
    result = matcher.match(
        MatchCandidate(title="Apple iPhone 15 128GB Black"),
        MatchCandidate(title="Apple iPhone 15 (Black, 128 GB)"),
    )
    assert result.status == MatchStatus.MATCH
    assert "same brand" in result.reasons
    assert "same storage" in result.reasons
    assert "same color" in result.reasons


def test_group_creates_separate_groups_per_variant():
    """The brief's SEARCH RESULT GROUPING example: 128GB Black, 256GB
    Black, and 128GB Blue must end up as three distinct groups."""
    matcher = ProductMatcher()
    candidates = [
        MatchCandidate(key="amazon-1", title="iPhone 15 128GB Black"),
        MatchCandidate(key="amazon-2", title="iPhone 15 256GB Black"),
        MatchCandidate(key="amazon-3", title="iPhone 15 128GB Blue"),
        MatchCandidate(key="flipkart-1", title="iPhone 15 Black 128GB"),
        MatchCandidate(key="flipkart-2", title="iPhone 15 Black 256GB"),
        MatchCandidate(key="flipkart-3", title="iPhone 15 Blue 128GB"),
    ]
    result = matcher.group(candidates)
    groups = result.groups
    assert len(groups) == 3

    def group_containing(key: str):
        return next(g for g in groups if key in g.members)

    g1 = group_containing("amazon-1")
    assert set(g1.members) == {"amazon-1", "flipkart-1"}

    g2 = group_containing("amazon-2")
    assert set(g2.members) == {"amazon-2", "flipkart-2"}

    g3 = group_containing("amazon-3")
    assert set(g3.members) == {"amazon-3", "flipkart-3"}


def test_group_does_not_merge_possible_matches_automatically():
    matcher = ProductMatcher()
    # A vague, attribute-free pair that can only ever land in
    # POSSIBLE_MATCH/NEEDS_REVIEW territory, never an auto-merged MATCH.
    candidates = [
        MatchCandidate(key="a", title="Wireless Bluetooth Earphones"),
        MatchCandidate(key="b", title="Bluetooth Wireless Earbuds"),
    ]
    grouping = matcher.group(candidates)
    assert len(grouping.groups) == 2  # never auto-merged into one group

    # But the pairwise comparison is still surfaced for manual review.
    result = grouping.pairwise_results[("a", "b")]
    assert result.status != MatchStatus.MATCH
    assert result.status in (MatchStatus.POSSIBLE_MATCH, MatchStatus.NEEDS_REVIEW, MatchStatus.NO_MATCH)
