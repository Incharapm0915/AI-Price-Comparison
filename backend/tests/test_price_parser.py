from app.parsers.price_parser import compute_discount_percent, parse_discount_percent, parse_price


def test_parse_price_with_currency_symbol_and_commas():
    assert parse_price("₹49,999.00") == 49999.0


def test_parse_price_rs_prefix():
    assert parse_price("Rs. 1,29,900") == 129900.0


def test_parse_price_dollar():
    assert parse_price("$699.99") == 699.99


def test_parse_price_none_when_no_number():
    assert parse_price("Currently unavailable") is None
    assert parse_price(None) is None


def test_parse_discount_percent():
    assert parse_discount_percent("(18% off)") == 18.0
    assert parse_discount_percent("-25%") == 25.0
    assert parse_discount_percent("no discount here") is None


def test_compute_discount_percent():
    assert compute_discount_percent(price=899.0, mrp=999.0) == 10.01
    assert compute_discount_percent(price=999.0, mrp=999.0) is None  # no real discount
    assert compute_discount_percent(price=None, mrp=999.0) is None
