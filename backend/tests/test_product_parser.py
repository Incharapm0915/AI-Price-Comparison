from app.parsers.product_parser import parse_availability
from app.parsers.seller_parser import parse_seller_name, parse_seller_rating
from app.parsers.specification_parser import parse_specification_table


def test_parse_availability_in_stock():
    assert parse_availability("In stock") == "IN_STOCK"
    assert parse_availability("Only 2 left in stock") == "IN_STOCK"


def test_parse_availability_out_of_stock():
    assert parse_availability("Out of Stock") == "OUT_OF_STOCK"


def test_parse_availability_unavailable():
    assert parse_availability("Currently unavailable") == "UNAVAILABLE"


def test_parse_availability_unknown_when_absent():
    assert parse_availability(None) == "UNKNOWN"
    assert parse_availability("Ships in 3-5 days") == "UNKNOWN"


def test_parse_seller_name_strips_prefix():
    assert parse_seller_name("Sold by Appario Retail Pvt Ltd") == "Appario Retail Pvt Ltd"
    assert parse_seller_name("RetailNet") == "RetailNet"
    assert parse_seller_name(None) is None


def test_parse_seller_rating():
    assert parse_seller_rating("4.3 out of 5") == 4.3


def test_parse_specification_table_cleans_units_and_drops_empty_rows():
    rows = [("RAM", "8 GB"), ("Storage:", "256 GB"), ("", "orphan value"), ("Weight", "")]
    specs = parse_specification_table(rows)
    assert specs == {"RAM": "8GB", "Storage": "256GB"}


def test_parse_specification_table_drops_rows_with_leaked_javascript():
    """Caught live against amazon.in: a "Customer Reviews" spec row can
    carry an inline ratings-widget script alongside its visible text,
    which .inner_text() picks up verbatim — that must never end up in the
    product's displayed specifications."""
    rows = [
        ("RAM", "8 GB"),
        (
            "Customer Reviews",
            "4.4 4.4 out of 5 stars (998) var dpAcrHasRegisteredArcLinkClickAction; "
            "P.when('A', 'ready').execute(function(A) { ... }); 4.4 out of 5 stars",
        ),
    ]
    specs = parse_specification_table(rows)
    assert specs == {"RAM": "8GB"}
    assert "Customer Reviews" not in specs
