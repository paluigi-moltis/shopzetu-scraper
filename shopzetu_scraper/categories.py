"""Category tree for shopzetu.com.

Built from the site's navigation menu (3 levels: category -> subcategory -> type).
Cross-cutting sections (Brands, New In, Sale, Budget Friendly, Shop by Body Fit,
Made in Africa, Trending) are excluded to minimise duplicates.

Structure (uniform for all categories)::

    CATEGORY_TREE = {
        "CategoryName": [           # top-level: Women, Men, Kids, Activewear, Beauty
            {
                "name":   "Subcategory Name",   # e.g. "Women's Dresses"
                "handle": "collection-handle",  # Shopify handle for this subcategory
                "types": {                      # finest granularity (may be empty)
                    "Type Name": "type-handle",
                    ...
                }
            },
            ...
        ],
    }

If ``types`` is non-empty, each type handle is scraped as a leaf collection
(3-level path: Category -> Subcategory -> Type).
If ``types`` is empty, the subcategory handle itself is the leaf
(2-level path: Category -> Subcategory).
"""

CATEGORY_TREE: dict[str, list[dict]] = {
    # ────────────────────────────── Women ──────────────────────────────
    "Women": [
        {
            "name": "Women's Dresses",
            "handle": "womens-dresses",
            "types": {
                "Bodycons": "bodycons",
                "Corset Dresses": "corset-dresses",
                "Knee Length Dresses": "knee-length-dress",
                "Maxi Dresses": "maxi-dresses",
                "Shirt Dresses": "shirt-dresses",
                "Kimono Sets": "kimono-sets",
            },
        },
        {
            "name": "Women's Tops",
            "handle": "womens-tops-top-categories",
            "types": {
                "Beachwear": "vacation-mode",
                "Bodysuits": "bodysuits-1",
                "Corset Tops": "corset-tops",
                "Crop Shirts": "crop-shirts",
                "Fitted Tops": "fitted-tops",
                "Loose Tops": "loose-tops",
            },
        },
        {
            "name": "Women's Bottoms",
            "handle": "womens-bottoms",
            "types": {
                "Denim Bottoms": "womens-denim-bottoms",
                "Full Length Pants": "full-length-pants",
                "Leggings": "leggings",
                "Loungewear": "loungewear",
                "Pant Sets": "pant-sets",
                "Short Sets": "short-sets",
            },
        },
        {
            "name": "Women's Skirts",
            "handle": "womens-skirts",
            "types": {
                "Denim Skirts": "denin-skirts",
                "Knee Length Skirts": "knee-length-skirts-1",
                "Mini Skirts": "mini-skirts",
                "Maxi Skirts": "full-length-skirts-1",
                "Skirt Suits": "skirt-suits",
            },
        },
        {
            "name": "Women's Innerwear",
            "handle": "womens-innerwear",
            "types": {
                "Bralettes": "bralettes",
                "Bras": "bras",
                "Lingerie": "lingerie",
                "Panties": "panties",
            },
        },
        {
            "name": "Women's Outerwear",
            "handle": "womens-outerwear",
            "types": {},
        },
        {
            "name": "Women's Footwear",
            "handle": "womens-footwear",
            "types": {
                "Boots": "boots",
                "Flats": "flats",
                "Heels": "heels",
                "Women's Sneakers": "womens-sneakers",
            },
        },
        {
            "name": "Women's Accessories",
            "handle": "womens-accessories",
            "types": {
                "Anklets": "anklets",
                "Aprons": "aprons",
                "Belly Chains": "belly-chains",
                "Bonnets": "bonnets",
                "Fitness Accessories": "fitness-accessories",
                "Fur Cuffs": "cuffs",
                "Gloves": "gloves",
                "Headgear": "headgear",
                "Jewellery": "jewelry",
                "Neckties": "neckties",
                "Sleeping Eye Masks": "sleeping-eye-masks",
                "Sunglasses Organizers": "sunglass-organizers",
                "Table Mats": "table-mats",
                "Waist Beads": "waist-beads",
            },
        },
    ],
    # ─────────────────────────────── Men ───────────────────────────────
    "Men": [
        {"name": "Men's Bottoms", "handle": "mens-bottoms", "types": {}},
        {"name": "Men's Suits", "handle": "mens-suits", "types": {}},
        {"name": "Men's Outerwear", "handle": "mens-outerwear", "types": {}},
        {"name": "Men's Accessories", "handle": "mens-accessories", "types": {}},
        {"name": "Men's Activewear", "handle": "mens-activewear", "types": {}},
        {"name": "Men's Shirts & T-Shirts", "handle": "mens-shirts-t-shirts", "types": {}},
        {
            "name": "Men's Footwear",
            "handle": "mens-footwear",
            "types": {
                "Men's Loafers": "mens-loafers",
                "Men's Boots": "mens-boots",
                "Men's Sneakers": "mens-sneakers",
                "Men's Slip On": "mens-slip-on",
                "Men's Oxford Shoes": "mens-oxford-shoes",
            },
        },
    ],
    # ─────────────────────────────── Kids ──────────────────────────────
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
    # ──────────────────────────── Activewear ───────────────────────────
    "Activewear": [
        {"name": "Activewear Sets", "handle": "activewear-sets", "types": {}},
        {"name": "Activewear Shorts", "handle": "activewear-shorts", "types": {}},
        {"name": "Activewear Tops", "handle": "activewear-tops", "types": {}},
        {"name": "Activewear Leggings", "handle": "leggings-1", "types": {}},
        {"name": "Activewear Sports Bras", "handle": "sports-bra", "types": {}},
        {"name": "Activewear Jackets", "handle": "activewear-jackets", "types": {}},
        {"name": "Activewear Jumpsuits", "handle": "activewear-jumpsuits", "types": {}},
    ],
    # ────────────────────────────── Beauty ─────────────────────────────
    "Beauty": [
        {
            "name": "Skincare",
            "handle": "beauty",
            "types": {
                "Sunscreens": "sunscreens",
                "Serums": "anti-aging-serum",
                "Handcare": "handcare",
                "Cleansers and Soaps": "cleansers-and-soaps",
                "Moisturisers and Creams": "moisturisers-and-creams",
                "Treatments": "treatments",
                "Deos & Lotions": "deos-lotions",
            },
        },
        {
            "name": "Makeup & Nails",
            "handle": "beauty",
            "types": {
                "Makeup": "make-up",
                "Nail Treatment": "nail-treatment",
            },
        },
        {
            "name": "Hair & Fragrance",
            "handle": "beauty",
            "types": {
                "Haircare": "hair",
                "Fragrances": "fragrance",
            },
        },
        {
            "name": "Lip Care",
            "handle": "beauty",
            "types": {
                "Lip Balms": "lip-balms",
                "Lip Scrubs": "lip-scrubs",
            },
        },
        {
            "name": "Tools",
            "handle": "beauty",
            "types": {
                "Tools & Accessories": "tools-accessories",
            },
        },
    ],
}


def get_leaf_collections() -> list[dict]:
    """Flatten the tree into a list of leaf collections to scrape.

    Each item is a dict with keys:
        - category (top-level)
        - subcategory
        - handle (Shopify collection handle to query via API)
        - type (finest-grain label, or None if subcategory == leaf)
    """
    leaves = []
    for category, subcats in CATEGORY_TREE.items():
        for sub in subcats:
            if sub["types"]:
                for type_name, type_handle in sub["types"].items():
                    leaves.append(
                        {
                            "category": category,
                            "subcategory": sub["name"],
                            "type": type_name,
                            "handle": type_handle,
                        }
                    )
            else:
                leaves.append(
                    {
                        "category": category,
                        "subcategory": sub["name"],
                        "type": None,
                        "handle": sub["handle"],
                    }
                )
    return leaves
