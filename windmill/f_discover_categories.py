"""
Step 1 — Discover the category structure from shopzetu.com.

Windmill script (type: python). Returns a list of leaf-collection dicts that
Step 2 (f_scrape_collection) iterates over.

Output schema (list[dict]):
    [
        {
            "category":     "Women",
            "subcategory":  "Women's Dresses",
            "type":         "Maxi Dresses",   # null if only 2 levels
            "handle":       "maxi-dresses",
            "product_count_estimate": 1675,
        },
        ...
    ]

Windmill variables required:
    u/paluigi/vps3_proxy  — proxy URL for HTTP requests

Usage in Windmill:
    Schedule or flow step → output is a list of dicts.
    Connect to Step 2 via "forloop" on this output.
"""

import random
import time

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

# ─── Category tree (from shopzetu_scraper.categories) ───
# Duplicated inline so the Windmill script is fully self-contained.
CATEGORY_TREE: dict[str, list[dict]] = {
    "Women": [
        {"name": "Women's Dresses", "handle": "womens-dresses", "types": {
            "Bodycons": "bodycons", "Corset Dresses": "corset-dresses",
            "Knee Length Dresses": "knee-length-dress", "Maxi Dresses": "maxi-dresses",
            "Shirt Dresses": "shirt-dresses", "Kimono Sets": "kimono-sets"}},
        {"name": "Women's Tops", "handle": "womens-tops-top-categories", "types": {
            "Beachwear": "vacation-mode", "Bodysuits": "bodysuits-1",
            "Corset Tops": "corset-tops", "Crop Shirts": "crop-shirts",
            "Fitted Tops": "fitted-tops", "Loose Tops": "loose-tops"}},
        {"name": "Women's Bottoms", "handle": "womens-bottoms", "types": {
            "Denim Bottoms": "womens-denim-bottoms", "Full Length Pants": "full-length-pants",
            "Leggings": "leggings", "Loungewear": "loungewear",
            "Pant Sets": "pant-sets", "Short Sets": "short-sets"}},
        {"name": "Women's Skirts", "handle": "womens-skirts", "types": {
            "Denim Skirts": "denin-skirts", "Knee Length Skirts": "knee-length-skirts-1",
            "Mini Skirts": "mini-skirts", "Maxi Skirts": "full-length-skirts-1",
            "Skirt Suits": "skirt-suits"}},
        {"name": "Women's Innerwear", "handle": "womens-innerwear", "types": {
            "Bralettes": "bralettes", "Bras": "bras",
            "Lingerie": "lingerie", "Panties": "panties"}},
        {"name": "Women's Outerwear", "handle": "womens-outerwear", "types": {}},
        {"name": "Women's Footwear", "handle": "womens-footwear", "types": {
            "Boots": "boots", "Flats": "flats", "Heels": "heels",
            "Women's Sneakers": "womens-sneakers"}},
        {"name": "Women's Accessories", "handle": "womens-accessories", "types": {
            "Anklets": "anklets", "Aprons": "aprons", "Belly Chains": "belly-chains",
            "Bonnets": "bonnets", "Fitness Accessories": "fitness-accessories",
            "Fur Cuffs": "cuffs", "Gloves": "gloves", "Headgear": "headgear",
            "Jewellery": "jewelry", "Neckties": "neckties",
            "Sleeping Eye Masks": "sleeping-eye-masks",
            "Sunglasses Organizers": "sunglass-organizers",
            "Table Mats": "table-mats", "Waist Beads": "waist-beads"}},
    ],
    "Men": [
        {"name": "Men's Bottoms", "handle": "mens-bottoms", "types": {}},
        {"name": "Men's Suits", "handle": "mens-suits", "types": {}},
        {"name": "Men's Outerwear", "handle": "mens-outerwear", "types": {}},
        {"name": "Men's Accessories", "handle": "mens-accessories", "types": {}},
        {"name": "Men's Activewear", "handle": "mens-activewear", "types": {}},
        {"name": "Men's Shirts & T-Shirts", "handle": "mens-shirts-t-shirts", "types": {}},
        {"name": "Men's Footwear", "handle": "mens-footwear", "types": {
            "Men's Loafers": "mens-loafers", "Men's Boots": "mens-boots",
            "Men's Sneakers": "mens-sneakers", "Men's Slip On": "mens-slip-on",
            "Men's Oxford Shoes": "mens-oxford-shoes"}},
    ],
    "Kids": [
        {"name": "Kids Dresses", "handle": "kids-dresses", "types": {}},
        {"name": "Kids Unisex Tops", "handle": "kids-unisex-tops", "types": {}},
        {"name": "Kids Outerwear", "handle": "kids-outerwear", "types": {}},
        {"name": "Kids Footwear", "handle": "kids-footwear", "types": {}},
        {"name": "Kid's Accessories", "handle": "kids-accessories-1", "types": {}},
        {"name": "Boy's Bottoms", "handle": "boys-bottoms", "types": {}},
        {"name": "Girl's Tops", "handle": "girls-tops", "types": {}},
        {"name": "Girl's Bottoms", "handle": "girls-bottoms", "types": {}},
    ],
    "Activewear": [
        {"name": "Activewear Sets", "handle": "activewear-sets", "types": {}},
        {"name": "Activewear Shorts", "handle": "activewear-shorts", "types": {}},
        {"name": "Activewear Tops", "handle": "activewear-tops", "types": {}},
        {"name": "Activewear Leggings", "handle": "leggings-1", "types": {}},
        {"name": "Activewear Sports Bras", "handle": "sports-bra", "types": {}},
        {"name": "Activewear Jackets", "handle": "activewear-jackets", "types": {}},
        {"name": "Activewear Jumpsuits", "handle": "activewear-jumpsuits", "types": {}},
    ],
    "Beauty": [
        {"name": "Skincare", "handle": "beauty", "types": {
            "Sunscreens": "sunscreens", "Serums": "anti-aging-serum",
            "Handcare": "handcare", "Cleansers and Soaps": "cleansers-and-soaps",
            "Moisturisers and Creams": "moisturisers-and-creams",
            "Treatments": "treatments", "Deos & Lotions": "deos-lotions"}},
        {"name": "Makeup & Nails", "handle": "beauty", "types": {
            "Makeup": "make-up", "Nail Treatment": "nail-treatment"}},
        {"name": "Hair & Fragrance", "handle": "beauty", "types": {
            "Haircare": "hair", "Fragrances": "fragrance"}},
        {"name": "Lip Care", "handle": "beauty", "types": {
            "Lip Balms": "lip-balms", "Lip Scrubs": "lip-scrubs"}},
        {"name": "Tools", "handle": "beauty", "types": {
            "Tools & Accessories": "tools-accessories"}},
    ],
}


def _flatten_tree() -> list[dict]:
    """Flatten CATEGORY_TREE into a list of leaf-collection dicts."""
    leaves: list[dict] = []
    for category, subcats in CATEGORY_TREE.items():
        for sub in subcats:
            if sub["types"]:
                for type_name, type_handle in sub["types"].items():
                    leaves.append({
                        "category": category,
                        "subcategory": sub["name"],
                        "type": type_name,
                        "handle": type_handle,
                    })
            else:
                leaves.append({
                    "category": category,
                    "subcategory": sub["name"],
                    "type": None,
                    "handle": sub["handle"],
                })
    return leaves


def _make_session() -> requests.Session:
    """Create a requests session with proxy and headers."""
    s = requests.Session()
    s.headers.update(HEADERS)
    if PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    return s


def _count_products(handle: str, session: requests.Session) -> int:
    """Estimate product count for a collection by paginating until exhausted."""
    total = 0
    cursor = None
    while True:
        time.sleep(random.randint(8, 15) / 10)
        url = f"{BASE_URL}{API_PATH.format(handle=handle)}?first=250"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code != 200:
                break
            data = resp.json()
            total += len(data.get("products", []))
            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        except Exception:
            break
    return total


def main() -> list[dict]:
    """Discover all leaf collections and return them with product count estimates.

    Returns a list of dicts, each with keys:
        category, subcategory, type, handle, product_count_estimate
    """
    session = _make_session()
    leaves = _flatten_tree()

    results = []
    for i, leaf in enumerate(leaves, 1):
        label = f"{leaf['category']} > {leaf['subcategory']}"
        if leaf["type"]:
            label += f" > {leaf['type']}"

        count = _count_products(leaf["handle"], session)
        results.append({
            "category": leaf["category"],
            "subcategory": leaf["subcategory"],
            "type": leaf["type"],
            "handle": leaf["handle"],
            "product_count_estimate": count,
        })
        print(f"[{i}/{len(leaves)}] {label}: {count} products")

    print(f"\nDiscovered {len(results)} collections, "
          f"{sum(r['product_count_estimate'] for r in results)} total products")
    return results
