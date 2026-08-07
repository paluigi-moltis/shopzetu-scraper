"""
Step 3 — Insert scraped products into MongoDB.

Windmill script (type: python). Receives the output of Step 2
(f_scrape_collection) and upserts all products into MongoDB.

Products are deduplicated by ``product_id`` (Shopify GID). When the same
product appears under multiple category paths (e.g. in two collections),
paths are aggregated into a ``categories`` array via ``$addToSet``.

Windmill variables required:
    u/paluigi/mongo_uri   — MongoDB connection string

Windmill flow:
    Step 2 output  →  this script
"""

from typing import Any

from pymongo import ASCENDING, MongoClient, UpdateOne

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
    """Upsert a batch of scraped products into MongoDB.

    Parameters (all from Step 2 output):
        category, subcategory, type, handle  — metadata
        product_count                        — number of products
        products                             — list of transformed product dicts
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLLECTION_NAME]

    # Ensure indexes (idempotent)
    coll.create_index([("product_id", ASCENDING)], unique=True)
    coll.create_index([("handle", ASCENDING)])
    coll.create_index([("brand", ASCENDING)])

    ops: list[UpdateOne] = []

    for product in products:
        product_id = product["product_id"]
        # Separate the category_path so it goes into the aggregate array
        cat_path = product.pop("category_path", None)

        update_doc: dict[str, Any] = {"$set": product}
        if cat_path:
            update_doc["$addToSet"] = {"categories": cat_path}

        ops.append(UpdateOne({"product_id": product_id}, update_doc, upsert=True))

    if ops:
        result = coll.bulk_write(ops, ordered=False)
        summary = {
            "handle": handle,
            "category": category,
            "subcategory": subcategory,
            "type": type,
            "input_count": product_count,
            "matched": result.matched_count,
            "upserted": result.upserted_count,
            "modified": result.modified_count,
            "total_in_db": coll.count_documents({}),
        }
    else:
        summary = {
            "handle": handle,
            "input_count": 0,
            "total_in_db": coll.count_documents({}),
        }

    client.close()
    print(f"Inserted {product_count} products for {handle}: {summary}")
    return summary
