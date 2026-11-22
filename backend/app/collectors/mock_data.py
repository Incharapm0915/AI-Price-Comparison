"""Mock product catalog.

Each entry is one physical product with the variant axes it comes in
(storage/RAM/color/size). `expand_catalog()` turns this into one row per
retailer per variant, wording the title *differently* per retailer on
purpose — this is the exact "same product, different title" problem the
matcher (Phase 5) has to solve, e.g.:

    Amazon:   "Samsung Galaxy S24 5G AI Smartphone, 8GB RAM, 256GB, Black"
    Flipkart: "Samsung Galaxy S24 (Black, 256 GB) 8 GB RAM"

A few products are deliberately retailer-exclusive (only on Amazon or only
on Flipkart) so the matcher/grouping also has real NO_MATCH cases to get
right, not just guaranteed pairs.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from itertools import product as _iterproduct


@dataclass
class CatalogEntry:
    brand: str
    model: str
    category: str
    subcategory: str
    base_specifications: dict[str, str]
    base_price: int  # INR, for the first storage/size tier
    rating: float
    rating_count: int
    storage_options: list[str] = field(default_factory=list)  # e.g. ["128GB", "256GB"]
    ram_options: list[str] = field(default_factory=list)       # e.g. ["6GB", "8GB"]
    colors: list[str] = field(default_factory=list)
    size_options: list[str] = field(default_factory=list)      # e.g. TV screen sizes
    only_on: str | None = None  # "amazon" | "flipkart" | None (both)
    highlights: list[str] = field(default_factory=list)


CATALOG: list[CatalogEntry] = [
    CatalogEntry(
        brand="Samsung", model="Galaxy S24", category="Electronics", subcategory="Smartphones",
        base_specifications={"Display": "6.2 inch Dynamic AMOLED", "Processor": "Exynos 2400",
                              "Camera": "50MP Triple Camera", "Battery": "4000 mAh", "OS": "Android 14"},
        base_price=64999, rating=4.4, rating_count=9800,
        storage_options=["128GB", "256GB"], ram_options=["8GB"], colors=["Black", "Violet"],
        highlights=["AI-powered camera", "120Hz display", "5G ready"],
    ),
    CatalogEntry(
        brand="Apple", model="iPhone 15", category="Electronics", subcategory="Smartphones",
        base_specifications={"Display": "6.1 inch Super Retina XDR", "Processor": "A16 Bionic",
                              "Camera": "48MP Dual Camera", "Battery": "3349 mAh", "OS": "iOS 17"},
        base_price=69900, rating=4.6, rating_count=15200,
        storage_options=["128GB", "256GB"], ram_options=["6GB"], colors=["Black", "Blue"],
        highlights=["USB-C", "Dynamic Island", "A16 Bionic chip"],
    ),
    CatalogEntry(
        brand="OnePlus", model="12R", category="Electronics", subcategory="Smartphones",
        base_specifications={"Display": "6.78 inch AMOLED", "Processor": "Snapdragon 8 Gen 2",
                              "Camera": "50MP Triple Camera", "Battery": "5500 mAh", "OS": "Android 14"},
        base_price=39999, rating=4.3, rating_count=6400,
        storage_options=["128GB", "256GB"], ram_options=["8GB", "16GB"], colors=["Cool Blue", "Iron Gray"],
        highlights=["100W SuperVOOC charging", "120Hz display"],
    ),
    CatalogEntry(
        brand="Apple", model="MacBook Air M2", category="Electronics", subcategory="Laptops",
        base_specifications={"Display": "13.6 inch Liquid Retina", "Processor": "Apple M2",
                              "RAM": "8GB", "Battery": "18 hours", "OS": "macOS"},
        base_price=99900, rating=4.7, rating_count=4200,
        storage_options=["256GB SSD", "512GB SSD"], colors=["Midnight", "Starlight"],
        highlights=["Fanless design", "MagSafe charging"],
    ),
    CatalogEntry(
        brand="Dell", model="XPS 13", category="Electronics", subcategory="Laptops",
        base_specifications={"Display": "13.4 inch FHD+", "Processor": "Intel Core i5-1340P",
                              "RAM": "16GB", "OS": "Windows 11"},
        base_price=89990, rating=4.2, rating_count=1850,
        storage_options=["512GB SSD"], colors=["Platinum Silver"],
        highlights=["InfinityEdge display", "Thunderbolt 4"],
    ),
    CatalogEntry(
        brand="Sony", model="WH-1000XM5", category="Electronics", subcategory="Headphones",
        base_specifications={"Type": "Over-Ear Wireless", "Battery Life": "30 hours",
                              "Noise Cancellation": "Active", "Bluetooth": "5.2"},
        base_price=29990, rating=4.6, rating_count=7300,
        colors=["Black", "Silver"],
        highlights=["Industry-leading noise cancellation", "Multipoint connection"],
    ),
    CatalogEntry(
        brand="boAt", model="Rockerz 550", category="Electronics", subcategory="Headphones",
        base_specifications={"Type": "Over-Ear Wireless", "Battery Life": "20 hours",
                              "Bluetooth": "5.0"},
        base_price=1999, rating=4.1, rating_count=52000,
        colors=["Black", "Blue"],
        highlights=["Padded ear cushions", "40mm dynamic drivers"],
    ),
    CatalogEntry(
        brand="Samsung", model="Crystal 4K UHD Smart TV", category="Electronics", subcategory="Televisions",
        base_specifications={"Resolution": "4K UHD", "HDR": "HDR10+", "Smart Platform": "Tizen"},
        base_price=42990, rating=4.3, rating_count=3100,
        size_options=["43 inch", "55 inch"],
        highlights=["Crystal processor 4K", "Built-in voice assistant"],
    ),
    CatalogEntry(
        brand="LG", model="UQ7500 4K Smart TV", category="Electronics", subcategory="Televisions",
        base_specifications={"Resolution": "4K UHD", "HDR": "HDR10", "Smart Platform": "webOS"},
        base_price=38990, rating=4.2, rating_count=980,
        size_options=["50 inch", "55 inch"],
        highlights=["AI-powered upscaling", "Magic Remote compatible"],
    ),
    CatalogEntry(
        brand="Apple", model="Watch Series 9", category="Electronics", subcategory="Smartwatches",
        base_specifications={"Display": "45mm Retina LTPO OLED", "Battery Life": "18 hours",
                              "Water Resistance": "50m"},
        base_price=41900, rating=4.7, rating_count=2600,
        colors=["Midnight", "Starlight"],
        highlights=["Double Tap gesture", "Always-On display"],
    ),
    CatalogEntry(
        brand="Xiaomi", model="Redmi Note 13 Pro", category="Electronics", subcategory="Smartphones",
        base_specifications={"Display": "6.67 inch AMOLED", "Processor": "Snapdragon 7s Gen 2",
                              "Camera": "200MP OIS Camera", "Battery": "5100 mAh", "OS": "Android 13"},
        base_price=25999, rating=4.2, rating_count=18400,
        storage_options=["128GB", "256GB"], ram_options=["8GB"], colors=["Aurora Purple", "Midnight Black"],
        highlights=["200MP OIS camera", "67W turbo charging"],
    ),
    # Retailer-exclusive products — genuine NO_MATCH / single-platform cases.
    CatalogEntry(
        brand="Amazon", model="Echo Dot (5th Gen)", category="Electronics", subcategory="Smart Speakers",
        base_specifications={"Connectivity": "Wi-Fi, Bluetooth", "Assistant": "Alexa"},
        base_price=4499, rating=4.4, rating_count=41000,
        colors=["Charcoal", "Glacier White"],
        only_on="amazon",
        highlights=["Improved audio", "Built-in temperature sensor"],
    ),
    CatalogEntry(
        brand="MarQ", model="43 inch Full HD Smart LED TV", category="Electronics", subcategory="Televisions",
        base_specifications={"Resolution": "Full HD", "Smart Platform": "Android TV"},
        base_price=19999, rating=3.9, rating_count=6200,
        size_options=["43 inch"],
        only_on="flipkart",
        highlights=["Flipkart in-house brand", "Android TV 11"],
    ),
]


AMAZON_SELLERS = ["Appario Retail Pvt Ltd", "Cloudtail India", "RetailNet", "Amazon.in"]
FLIPKART_SELLERS = ["SuperComNet", "RetailEZ Pvt Ltd", "OmniTech Retail", "Flipkart Wholesale"]


def _phone_amazon_title(entry: CatalogEntry, storage: str, ram: str | None, color: str) -> str:
    ram_part = f", {ram} RAM" if ram else ""
    return f"{entry.brand} {entry.model} 5G Smartphone{ram_part}, {storage}, {color}"


def _phone_flipkart_title(entry: CatalogEntry, storage: str, ram: str | None, color: str) -> str:
    ram_part = f" {ram} RAM" if ram else ""
    return f"{entry.brand} {entry.model} ({color}, {storage}){ram_part}"


def _laptop_amazon_title(entry: CatalogEntry, storage: str, color: str) -> str:
    return f"{entry.brand} {entry.model} Laptop, {entry.base_specifications.get('RAM', '')} RAM, {storage}, {color}"


def _laptop_flipkart_title(entry: CatalogEntry, storage: str, color: str) -> str:
    return f"{entry.brand} {entry.model} ({color}) - {storage} {entry.base_specifications.get('RAM', '')} RAM"


def _headphone_amazon_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} Wireless Headphones, {color}"


def _headphone_flipkart_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} Bluetooth Headset ({color})"


def _tv_amazon_title(entry: CatalogEntry, size: str) -> str:
    return f"{entry.brand} {size} {entry.model}"


def _tv_flipkart_title(entry: CatalogEntry, size: str) -> str:
    return f"{entry.brand} {size.replace(' inch', '')} inches {entry.model}"


def _watch_amazon_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} GPS, {color} Aluminium Case"


def _watch_flipkart_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} ({color})"


def _default_amazon_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} - {color}" if color else f"{entry.brand} {entry.model}"


def _default_flipkart_title(entry: CatalogEntry, color: str) -> str:
    return f"{entry.brand} {entry.model} ({color})" if color else f"{entry.brand} {entry.model}"


def _variant_price(entry: CatalogEntry, storage_index: int) -> int:
    # Each storage tier up costs ~18% more, rounded to nearest 100.
    return int(round(entry.base_price * (1.18 ** storage_index) / 100) * 100)


def _title_and_variant(entry: CatalogEntry, retailer: str) -> list[tuple[str, str, dict]]:
    """Returns [(title, variant_label, extra_specs)] for every variant
    combination of this catalog entry."""
    results: list[tuple[str, str, dict]] = []
    subcat = entry.subcategory

    if subcat == "Smartphones":
        rams = entry.ram_options or [None]
        for s_idx, storage in enumerate(entry.storage_options):
            for ram in rams:
                for color in entry.colors:
                    title = (
                        _phone_amazon_title(entry, storage, ram, color)
                        if retailer == "amazon"
                        else _phone_flipkart_title(entry, storage, ram, color)
                    )
                    variant_label = f"{storage} {color}" + (f" {ram} RAM" if ram else "")
                    extra = {"Storage": storage, "Color": color}
                    if ram:
                        extra["RAM"] = ram
                    extra["_price"] = _variant_price(entry, s_idx)
                    results.append((title, variant_label, extra))
    elif subcat == "Laptops":
        for s_idx, storage in enumerate(entry.storage_options):
            for color in entry.colors:
                title = (
                    _laptop_amazon_title(entry, storage, color)
                    if retailer == "amazon"
                    else _laptop_flipkart_title(entry, storage, color)
                )
                variant_label = f"{storage} {color}"
                extra = {"Storage": storage, "Color": color, "_price": _variant_price(entry, s_idx)}
                results.append((title, variant_label, extra))
    elif subcat == "Headphones":
        for color in entry.colors:
            title = (
                _headphone_amazon_title(entry, color)
                if retailer == "amazon"
                else _headphone_flipkart_title(entry, color)
            )
            extra = {"Color": color, "_price": entry.base_price}
            results.append((title, color, extra))
    elif subcat == "Televisions":
        for s_idx, size in enumerate(entry.size_options):
            title = (
                _tv_amazon_title(entry, size)
                if retailer == "amazon"
                else _tv_flipkart_title(entry, size)
            )
            extra = {"Screen Size": size, "_price": _variant_price(entry, s_idx)}
            results.append((title, size, extra))
    elif subcat == "Smartwatches":
        for color in entry.colors:
            title = (
                _watch_amazon_title(entry, color)
                if retailer == "amazon"
                else _watch_flipkart_title(entry, color)
            )
            extra = {"Color": color, "_price": entry.base_price}
            results.append((title, color, extra))
    else:
        colors = entry.colors or [""]
        for color in colors:
            title = (
                _default_amazon_title(entry, color)
                if retailer == "amazon"
                else _default_flipkart_title(entry, color)
            )
            extra = {"_price": entry.base_price}
            if color:
                extra["Color"] = color
            results.append((title, color or entry.model, extra))

    return results


def expand_catalog(retailer: str) -> list[dict]:
    """Expands CATALOG into one dict per retailer-listing-variant, with
    retailer-specific titles, IDs, sellers, and prices."""
    if retailer not in ("amazon", "flipkart"):
        raise ValueError(f"expand_catalog only supports amazon/flipkart, got {retailer!r}")

    sellers = AMAZON_SELLERS if retailer == "amazon" else FLIPKART_SELLERS
    out: list[dict] = []

    for entry in CATALOG:
        if entry.only_on and entry.only_on != retailer:
            continue

        for i, (title, variant_label, extra) in enumerate(_title_and_variant(entry, retailer)):
            price = extra.pop("_price")
            slug = f"{entry.brand}-{entry.model}-{variant_label}".lower()
            slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")
            # Deterministic across process restarts — Python's built-in
            # hash() is randomized per-process (PYTHONHASHSEED) for strings,
            # which would otherwise mint a *new* retailer_product_id every
            # time the app restarts, breaking the (retailer,
            # retailer_product_id) upsert key and silently accumulating
            # duplicate listings in the database on every restart.
            digest = hashlib.sha256(f"{retailer}:{slug}".encode()).hexdigest()
            retailer_product_id = f"{'B0' if retailer == 'amazon' else 'MOB'}{int(digest[:8], 16) % 10_000_000:07d}"
            specs = {**entry.base_specifications, **{k: v for k, v in extra.items()}}
            out.append(
                {
                    "retailer": retailer,
                    "retailer_product_id": retailer_product_id,
                    "slug": slug,
                    "product_name": title,
                    "brand": entry.brand,
                    "model": entry.model,
                    "variant": variant_label,
                    "category": entry.category,
                    "subcategory": entry.subcategory,
                    "specifications": specs,
                    "highlights": entry.highlights,
                    "base_price": price,
                    "rating": entry.rating,
                    "rating_count": entry.rating_count,
                    "seller_name": sellers[i % len(sellers)],
                }
            )
    return out
