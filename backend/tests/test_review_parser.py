from datetime import datetime

from app.parsers.review_parser import (
    parse_helpful_count,
    parse_rating_text,
    parse_review_date,
    parse_verified_purchase,
)


def test_parse_rating_out_of_5():
    assert parse_rating_text("4.5 out of 5 stars") == 4.5


def test_parse_rating_slash_format():
    assert parse_rating_text("4.5/5") == 4.5


def test_parse_rating_bare_number():
    assert parse_rating_text("4.5") == 4.5


def test_parse_rating_none_when_unparseable():
    assert parse_rating_text("no rating") is None
    assert parse_rating_text(None) is None


def test_parse_helpful_count():
    assert parse_helpful_count("23 people found this helpful") == 23
    assert parse_helpful_count("1 person found this helpful") == 1
    assert parse_helpful_count("1,204 people found this helpful") == 1204


def test_parse_helpful_count_none_when_absent():
    assert parse_helpful_count("") is None
    assert parse_helpful_count("Great product") is None


def test_parse_review_date():
    assert parse_review_date("Reviewed in India on 12 March 2024") == datetime(2024, 3, 12)


def test_parse_review_date_abbreviated_month():
    assert parse_review_date("12 Mar 2024") == datetime(2024, 3, 12)


def test_parse_review_date_none_when_unparseable():
    assert parse_review_date("recently") is None


def test_parse_verified_purchase():
    assert parse_verified_purchase("Verified Purchase") is True
    assert parse_verified_purchase("") is None
    assert parse_verified_purchase("Some other badge") is False
