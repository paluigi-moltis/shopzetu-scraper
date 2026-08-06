# shopzetu-scraper

Python scraper for [shopzetu.com](https://www.shopzetu.com/) — a Kenyan fashion e-commerce site built on Shopify Hydrogen.

## Overview

Discovers and queries the site's **hidden JSON API** (`/api/collections/{handle}/products`) instead of HTML scraping, returning clean structured product data with cursor-based pagination.

## Features

- **No HTML parsing** — uses the internal Shopify Hydrogen JSON API
- **3-level category taxonomy** (Category → Subcategory → Type) from the site menu
- **Cursor pagination** with configurable page size (up to 250/products/page)
- **Random delays** between all requests (1–3 s default, configurable)
- **Automatic retries** on transient HTTP errors (429, 502, 503, 504)
- **MongoDB storage** with deduplication by `product_id` and category-path aggregation
- Excludes cross-cutting sections (Brands, Sale, Trending, etc.) to minimise duplicates

## Requirements

- Python ≥ 3.11
- MongoDB (local or remote)

## Installation

```bash
git clone https://github.com/paluigi-moltis/shopzetu-scraper.git
cd shopzetu-scraper
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Usage

### Full scrape

```bash
python -m shopzetu_scraper.scraper
```

### Test run (1 page per collection)

```bash
python -m shopzetu_scraper.scraper --max-pages 1 --only Women
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--mongo-uri` | `mongodb://localhost:27017` | MongoDB connection string |
| `--db` | `shopzetu` | Database name |
| `--collection` | `products` | Collection name |
| `--max-pages N` | all | Limit pages per collection (testing) |
| `--only CATEGORY` | all | Only scrape one category (Women, Men, Kids, Activewear, Beauty) |
| `--delay-min S` | `1.0` | Min random delay between requests (seconds) |
| `--delay-max S` | `3.0` | Max random delay between requests (seconds) |
| `-v` | off | Debug-level logging |

## Data Model

Each product is stored as a MongoDB document keyed on `product_id` (Shopify GID). When the same product appears under multiple category paths, paths are aggregated into a `categories` array.

```json
{
  "product_id": "gid://shopify/Product/9399151984859",
  "handle": "vivo-amai-maxi-kaftan-...",
  "product_name": "Vivo Amai Maxi Kaftan In Textured Satin - ...",
  "brand": "Vivo",
  "price": "6500.0",
  "currency": "KES",
  "original_price": null,
  "product_url": "https://www.shopzetu.com/products/vivo-amai-maxi-kaftan-...",
  "created_at": "2026-07-10T13:28:28Z",
  "tags": ["AMAI", "DRESSES", "VIVO", "WOMEN"],
  "available_for_sale": true,
  "availability": {
    "for_sale": true,
    "num_variants": 1,
    "variants_available": 1
  },
  "price_range": {"min": "6500.0", "max": "6500.0", "currency": "KES"},
  "variants": [{"availableForSale": true, "price": {...}, "compareAtPrice": null, ...}],
  "categories": [
    {"category": "Women", "subcategory": "Women's Dresses", "type": "Maxi Dresses"}
  ]
}
```

## Project Structure

```
shopzetu_scraper/
├── __init__.py
├── categories.py   # 3-level category tree from site menu
├── client.py       # Async HTTP client for the hidden API
├── storage.py      # MongoDB layer with dedup + category aggregation
└── scraper.py      # CLI orchestrator (entry point)
tests/
└── test_scraper.py # Unit tests (categories, client, transform)
```

## License

MIT
