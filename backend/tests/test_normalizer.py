"""Phase 4 tests for ProductNormalizer — including the two exact examples
from the project brief."""
from app.matching.normalizer import ProductNormalizer

normalizer = ProductNormalizer()


def test_brief_example_samsung_parenthetical_format():
    result = normalizer.normalize("Samsung Galaxy S24 (Black, 256 GB)")
    assert result.brand == "Samsung"
    assert result.model == "Galaxy S24"
    assert result.storage_gb == 256
    assert result.color == "Black"


def test_brief_example_samsung_marketing_format():
    result = normalizer.normalize("SAMSUNG Galaxy S24 5G AI Smartphone 8GB 256GB Black")
    assert result.brand == "Samsung"
    assert result.model == "Galaxy S24"
    assert result.ram_gb == 8
    assert result.storage_gb == 256
    assert result.color == "Black"


def test_apple_iphone_amazon_style():
    result = normalizer.normalize("Apple iPhone 15 128GB Black")
    assert result.brand == "Apple"
    assert result.model == "iPhone 15"
    assert result.storage_gb == 128
    assert result.color == "Black"


def test_apple_iphone_flipkart_style():
    result = normalizer.normalize("Apple iPhone 15 (Black, 128 GB)")
    assert result.brand == "Apple"
    assert result.model == "iPhone 15"
    assert result.storage_gb == 128
    assert result.color == "Black"


def test_sony_headphones_amazon_style():
    result = normalizer.normalize("Sony WH-1000XM5 Wireless Headphones Black")
    assert result.brand == "Sony"
    assert "1000XM5" in result.model
    assert result.color == "Black"


def test_sony_headphones_flipkart_style():
    result = normalizer.normalize("Sony WH1000XM5 Bluetooth Headset (Black)")
    assert result.brand == "Sony"
    assert "1000XM5" in result.model
    assert result.color == "Black"


def test_multi_word_color_extraction():
    result = normalizer.normalize("OnePlus 12R (Cool Blue, 128 GB) 8 GB RAM")
    assert result.brand == "OnePlus"
    assert result.color == "Cool Blue"
    assert result.ram_gb == 8
    assert result.storage_gb == 128


def test_tb_storage_converted_to_gb():
    result = normalizer.normalize("Dell XPS 13 1TB SSD Platinum Silver")
    assert result.storage_gb == 1024


def test_no_brand_detected_leaves_none():
    result = normalizer.normalize("Unbranded Generic Cable 1m")
    assert result.brand is None


def test_normalized_title_is_lowercase_and_stable_regardless_of_input_case():
    a = normalizer.normalize("SAMSUNG GALAXY S24 (BLACK, 256 GB)")
    b = normalizer.normalize("samsung galaxy s24 (black, 256 gb)")
    assert a.normalized_title == b.normalized_title


def test_normalize_specifications_cleans_unit_spacing_without_dropping_keys():
    specs = {"RAM": "8 GB", "Storage": "256 GB", "Battery": "4000 mAh", "Weight": 168}
    cleaned = normalizer.normalize_specifications(specs)
    assert cleaned["RAM"] == "8GB"
    assert cleaned["Storage"] == "256GB"
    assert cleaned["Battery"] == "4000mAh"
    assert cleaned["Weight"] == 168  # non-string values pass through untouched


def test_build_common_product_id_matches_brief_example():
    slug = ProductNormalizer.build_common_product_id("Apple", "iPhone 15", 128, "Black")
    assert slug == "APPLE_IPHONE_15_128_BLACK"


def test_build_common_product_id_handles_missing_fields():
    slug = ProductNormalizer.build_common_product_id("Sony", "WH-1000XM5", None, "Black")
    assert slug == "SONY_WH_1000XM5_BLACK"
