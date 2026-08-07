"""
Step 3 — Insert scraped products into MongoDB.

Windmill script (type: python). Receives the output of Step 2
(f_scrape_collection) and bulk-inserts all products into MongoDB.

Simple insert — no index management, no upsert logic.
For weekly re-runs, delete the collection beforehand or run a cleanup step.

Windmill variables required:
    u/paluigi/mongo_uri   — MongoDB connection string

Windmill flow:
    Step 2 output  →  this script
"""

from datetime import date
from typing import Any

from pymongo import MongoClient

# ─── Windmill variables ───
try:
    import wmill

    MONGO_URI = wmill.get_variable("u/paluigi/mongo_uri")
except Exception:
    import os

    MONGO_URI = os.environ.get("WMILL_MONGO_URI", "mongodb://localhost:27017")

DB_NAME = "shopzetu"
COLLECTION_NAME = "products"


def main(
    category: str,
    subcategory: str,
    type: str | None,
    handle: str,
    product_count: int,
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bulk-insert a batch of scraped products into MongoDB.

    Parameters (all from Step 2 output):
        category, subcategory, type, handle  — metadata
        product_count                        — number of products
        products                             — list of transformed product dicts
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLLECTION_NAME]

    today = date.today().isoformat()  # "2026-08-07"

    docs = []
    for product in products:
        # Flatten category_path into top-level fields for easy querying
        cat_path = product.pop("category_path", None)
        if cat_path:
            product["category"] = cat_path.get("category")
            product["subcategory"] = cat_path.get("subcategory")
            product["type"] = cat_path.get("type")

        product["scraped_at"] = today
        docs.append(product)

    if docs:
        coll.insert_many(docs, ordered=False)
        total_in_db = coll.count_documents({})
    else:
        total_in_db = coll.count_documents({})

    client.close()

    summary = {
        "category": category,
        "subcategory": subcategory,
        "type": type,
        "handle": handle,
        "inserted": len(docs),
        "total_in_db": total_in_db,
    }
    print(f"Inserted {len(docs)} products for {handle}: {summary}")
    return summary
