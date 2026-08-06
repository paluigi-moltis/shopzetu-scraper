"""Main scraper orchestrator.

Usage::

    python -m shopzetu_scraper           # full scrape
    python -m shopzetu_scraper --max-pages 1  # test: 1 page per collection
    python -m shopzetu_scraper --only Women   # only one category
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .categories import get_leaf_collections
from .client import ShopzetuClient
from .storage import ProductStore

logger = logging.getLogger("shopzetu_scraper")


async def scrape(
    store: ProductStore,
    *,
    max_pages: int | None = None,
    only_category: str | None = None,
) -> None:
    """Scrape all leaf collections and store products in MongoDB.

    Parameters
    ----------
    max_pages
        If set, only fetch this many pages per collection (for testing).
    only_category
        If set, only scrape collections under this top-level category.
    """
    leaves = get_leaf_collections()

    if only_category:
        leaves = [l for l in leaves if l["category"] == only_category]
        logger.info("Filtered to category '%s': %d collections", only_category, len(leaves))
    else:
        logger.info("Scraping all %d leaf collections", len(leaves))

    async with ShopzetuClient() as client:
        for i, leaf in enumerate(leaves, 1):
            label = f"{leaf['category']} > {leaf['subcategory']}"
            if leaf["type"]:
                label += f" > {leaf['type']}"

            logger.info("[%d/%d] Scraping: %s (handle=%s)", i, len(leaves), label, leaf["handle"])

            try:
                products = await client.fetch_all(leaf["handle"], max_pages=max_pages)
            except Exception:
                logger.exception("Failed to scrape collection '%s'", leaf["handle"])
                continue

            if products:
                stored = store.upsert_products(
                    products,
                    category=leaf["category"],
                    subcategory=leaf["subcategory"],
                    type_name=leaf["type"],
                )
                logger.info("  → %d products fetched, %d upserted", len(products), stored)
            else:
                logger.info("  → 0 products (empty collection)")

    logger.info("Scrape complete. Total products in DB: %d", store.count())


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape shopzetu.com products into MongoDB")
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection string (default: %(default)s)",
    )
    parser.add_argument("--db", default="shopzetu", help="MongoDB database name (default: %(default)s)")
    parser.add_argument(
        "--collection",
        default="products",
        help="MongoDB collection name (default: %(default)s)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages per collection (for testing; default: all)",
    )
    parser.add_argument(
        "--only",
        dest="only_category",
        default=None,
        help="Only scrape this top-level category (Women, Men, Kids, Activewear, Beauty)",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=1.0,
        help="Min random delay between requests in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=3.0,
        help="Max random delay between requests in seconds (default: %(default)s)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    store = ProductStore(
        connection_string=args.mongo_uri,
        db_name=args.db,
        collection_name=args.collection,
    )

    try:
        asyncio.run(
            scrape(
                store,
                max_pages=args.max_pages,
                only_category=args.only_category,
            )
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    finally:
        store.close()


if __name__ == "__main__":
    main()
