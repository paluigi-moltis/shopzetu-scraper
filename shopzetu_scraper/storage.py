"""MongoDB storage layer for scraped products.

Each product is stored (upserted) keyed on ``product_id`` (the Shopify GID).
Because the same product may appear under multiple category/subcategory/type
paths, we *aggregate* category info rather than overwrite: every new path
encountered is appended to a ``categories`` array on the document.
"""

from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, MongoClient, UpdateOne

logger = logging.getLogger(__name__)

DEFAULT_DB = "shopzetu"
DEFAULT_COLLECTION = "products"


def _build_category_doc(
    category: str,
    subcategory: str,
    type_name: str | None,
) -> dict[str, str | None]:
    """Build a single category-path sub-document."""
    return {"category": category, "subcategory": subcategory, "type": type_name}


def _transform_product(
    raw: dict[str, Any],
    category: str,
    subcategory: str,
    type_name: str | None,
) -> dict[str, Any]:
    """Transform a raw API product into the document shape we store.

    Flattens price/availability fields and attaches the category path.
    """
    variants = raw.get("variants", {}).get("nodes", [])
    price_range = raw.get("priceRange", {})

    # Determine original price: use the first variant with a compareAtPrice, else None
    original_price = None
    original_currency = None
    for v in variants:
        cap = v.get("compareAtPrice")
        if cap and float(cap.get("amount", 0)) > 0:
            original_price = cap["amount"]
            original_currency = cap.get("currencyCode")
            break

    # Current price from priceRange (min is the display price)
    min_price = price_range.get("minVariantPrice", {})
    max_price = price_range.get("maxVariantPrice", {})

    # Per-variant availability: any variant for sale?
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
        "category_path": _build_category_doc(category, subcategory, type_name),
    }


class ProductStore:
    """MongoDB-backed product store with dedup-by-product_id and category aggregation."""

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        db_name: str = DEFAULT_DB,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.collection.create_index([("product_id", ASCENDING)], unique=True)
        self.collection.create_index([("handle", ASCENDING)])
        self.collection.create_index([("brand", ASCENDING)])
        self.collection.create_index([("category_path.category", ASCENDING)])

    def upsert_products(
        self,
        raw_products: list[dict[str, Any]],
        category: str,
        subcategory: str,
        type_name: str | None,
    ) -> int:
        """Bulk-upsert a batch of raw API products.

        For existing products, appends the category path if not already present
        and merges any fields that may have changed (price, availability, etc.).
        Returns the number of upsert operations.
        """
        ops: list[UpdateOne] = []
        cat_doc = _build_category_doc(category, subcategory, type_name)

        for raw in raw_products:
            doc = _transform_product(raw, category, subcategory, type_name)
            product_id = doc["product_id"]

            # Pull category_path out — it goes into an array
            cat_path = doc.pop("category_path")

            ops.append(
                UpdateOne(
                    {"product_id": product_id},
                    {
                        # Set all fields on first insert, update mutable ones on existing
                        "$set": doc,
                        # Add category path only if not already present
                        "$addToSet": {"categories": cat_path},
                    },
                    upsert=True,
                )
            )

        if ops:
            result = self.collection.bulk_write(ops, ordered=False)
            logger.info(
                "Upserted %d products for %s/%s/%s (matched=%d, upserted=%d, modified=%d)",
                len(ops),
                category,
                subcategory,
                type_name or "-",
                result.matched_count,
                result.upserted_count,
                result.modified_count,
            )
            return len(ops)
        return 0

    def count(self) -> int:
        return self.collection.count_documents({})

    def close(self) -> None:
        self.client.close()
