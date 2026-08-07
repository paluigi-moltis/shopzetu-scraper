"""
Step 2 — Scrape all products from a single collection (leaf).

Windmill script (type: python). Designed to be called once per element of the
list produced by Step 1 (f_discover_categories). In Windmill, use a **forloop**
step that iterates over the Step-1 output list and calls this script for each item.

Output schema (dict):
    {
        "category":          "Women",
        "subcategory":       "Women's Dresses",
        "type":              "Maxi Dresses",
        "handle":            "maxi-dresses",
        "product_count":     1675,
        "products":          [ {...}, {...}, ... ]   # transformed product dicts
    }

Windmill variables required:
    u/paluigi/vps3_proxy  — proxy URL for HTTP requests

Windmill flow:
    Step 1 output  →  forloop  →  this script (one call per item)
    this output    →  Step 3 (f_insert_mongodb)
"""

import random
import time
from typing import Any

import requests

# ─── Windmill variable ───
try:
    import wmill

    PROXY = wmill.get_variable("u/paluigi/vps3_proxy")
except Exception:
    import os

    PROXY = os.environ.get("WMILL_PROXY", "")

# ─── Config ───
BASE_URL = "https://www.shopzetu.com"
API_PATH = "/api/collections/{handle}/products"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
    "Accept": "application/json",
}
PAGE_SIZE = 250


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    return s


def _fetch_all_pages(handle: str, session: requests.Session) -> list[dict[str, Any]]:
    """Paginate through the hidden API and return all raw product dicts."""
    all_products: list[dict[str, Any]] = []
    cursor = None
    page = 0

    while True:
        time.sleep(random.randint(8, 15) / 10)
        url = f"{BASE_URL}{API_PATH.format(handle=handle)}?first={PAGE_SIZE}"
        if cursor:
            url += f"&cursor={cursor}"

        resp = None
        for attempt in range(1, 4):
            try:
                resp = session.get(url, timeout=30)
                if resp.status_code == 200:
                    break
                if resp.status_code in (429, 502, 503, 504):
                    wait = 2 ** attempt
                    print(f"  Transient {resp.status_code}, retrying in {wait}s")
                    time.sleep(wait)
                    continue
                print(f"  HTTP {resp.status_code}, skipping remaining pages")
                return all_products
            except requests.RequestException as exc:
                if attempt == 3:
                    print(f"  Request failed after 3 retries: {exc}")
                    return all_products
                time.sleep(2 ** attempt)

        if resp is None or resp.status_code != 200:
            return all_products

        data = resp.json()
        products = data.get("products", [])
        all_products.extend(products)
        page += 1
        print(f"  Page {page}: +{len(products)} (total {len(all_products)})")

        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return all_products


def _transform_product(
    raw: dict[str, Any],
    category: str,
    subcategory: str,
    type_name: str | None,
) -> dict[str, Any]:
    """Transform a raw API product into the final document shape.

    This is the same logic as shopzetu_scraper.storage._transform_product,
    duplicated here so the Windmill script is fully self-contained.
    """
    variants = raw.get("variants", {}).get("nodes", [])
    price_range = raw.get("priceRange", {})

    original_price = None
    original_currency = None
    for v in variants:
        cap = v.get("compareAtPrice")
        if cap and float(cap.get("amount", 0)) > 0:
            original_price = cap["amount"]
            original_currency = cap.get("currencyCode")
            break

    min_price = price_range.get("minVariantPrice", {})
    max_price = price_range.get("maxVariantPrice", {})
    available_for_sale = any(v.get("availableForSale", False) for v in variants)

    return {
        "product_id": raw["id"],
        "handle": raw["handle"],
        "product_name": raw["title"],
        "brand": raw.get("vendor"),
        "price": min_price.get("amount"),
        "currency": min_price.get("currencyCode"),
        "original_price": original_price,
        "original_currency": original_currency,
        "product_url": f"https://www.shopzetu.com/products/{raw['handle']}",
        "created_at": raw.get("createdAt"),
        "tags": raw.get("tags", []),
        "available_for_sale": available_for_sale,
        "availability": {
            "for_sale": available_for_sale,
            "num_variants": len(variants),
            "variants_available": sum(1 for v in variants if v.get("availableForSale")),
        },
        "price_range": {
            "min": min_price.get("amount"),
            "max": max_price.get("amount"),
            "currency": min_price.get("currencyCode"),
        },
        "variants": variants,
        "category_path": {
            "category": category,
            "subcategory": subcategory,
            "type": type_name,
        },
    }


def main(
    category: str,
    subcategory: str,
    handle: str,
    type: str | None = None,
) -> dict[str, Any]:
    """Scrape a single collection and return transformed products.

    Parameters (passed from Step 1 output via Windmill forloop):
        category:     top-level category name
        subcategory:  second-level name
        handle:       Shopify collection handle to query via API
        type:         third-level type name (or None)
    """
    label = f"{category} > {subcategory}"
    if type:
        label += f" > {type}"
    print(f"Scraping: {label} (handle={handle})")

    session = _make_session()
    raw_products = _fetch_all_pages(handle, session)
    print(f"Fetched {len(raw_products)} raw products")

    products = [
        _transform_product(raw, category, subcategory, type)
        for raw in raw_products
    ]

    return {
        "category": category,
        "subcategory": subcategory,
        "type": type,
        "handle": handle,
        "product_count": len(products),
        "products": products,
    }
