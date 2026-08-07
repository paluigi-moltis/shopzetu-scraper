# Shopzetu Scraper — Windmill Scripts

Three self-contained Python scripts designed to run as Windmill flow steps.
Each script is a standalone `main()` function — no shared imports between them.

## Architecture

```
┌─────────────────────────┐     ┌───────────────────────────┐     ┌─────────────────────────┐
│  Step 1                 │     │  Step 2 (forloop)         │     │  Step 3                 │
│  f_discover_categories  │────▶│  f_scrape_collection       │────▶│  f_insert_mongodb       │
│                         │     │  (one call per item)       │     │                         │
│  Output: list[dict]     │     │  Output: dict with products│     │  Upserts into MongoDB   │
└─────────────────────────┘     └───────────────────────────┘     └─────────────────────────┘
```

## Step 1 — `f_discover_categories.py`

**Purpose:** Builds the full category tree and estimates product counts.

**Input:** None (reads the hardcoded category tree + queries the API for counts)

**Output:** `list[dict]`
```json
[
  {
    "category": "Women",
    "subcategory": "Women's Dresses",
    "type": "Maxi Dresses",
    "handle": "maxi-dresses",
    "product_count_estimate": 1675
  }
]
```

**Windmill config:** This is a regular step. Its output list is consumed by Step 2.

## Step 2 — `f_scrape_collection.py`

**Purpose:** Scrapes all products from a single collection via the hidden API.

**Input:** One element from the Step 1 list (via Windmill **forloop**):
```json
{
  "category": "Women",
  "subcategory": "Women's Dresses",
  "type": "Maxi Dresses",
  "handle": "maxi-dresses"
}
```

**Output:** `dict` with all transformed products
```json
{
  "category": "Women",
  "subcategory": "Women's Dresses",
  "type": "Maxi Dresses",
  "handle": "maxi-dresses",
  "product_count": 1675,
  "products": [ { ... }, { ... }, ... ]
}
```

**Windmill config:** Set as a **forloop** step. The iterator input should be
mapped from Step 1's output. Each iteration calls `main()` with that item's
`category`, `subcategory`, `type`, and `handle` fields.

## Step 3 — `f_insert_mongodb.py`

**Purpose:** Upserts the scraped products into MongoDB.

**Input:** The full output of Step 2 (category metadata + products list).

**Output:** Summary dict (counts of matched/upserted/modified)

**Windmill config:** This receives the forloop's aggregated output. In a
Windmill flow, connect it to collect all Step 2 outputs. Alternatively, if
you want each collection inserted independently (more resilient), put Step 3
inside the forloop right after Step 2.

## Windmill Variables

Create these variables in your Windmill workspace:

| Variable path | Description | Example |
|---|---|---|
| `u/paluigi/vps3_proxy` | HTTP/HTTPS proxy URL | `http://user:pass@host:port` |
| `u/paluigi/mongo_uri` | MongoDB connection string | `mongodb+srv://...` |

## Windmill Flow Setup

1. **Create a Flow** with 3 steps.
2. Step 1 → `f_discover_categories` (type: python).
3. Step 2 → `f_scrape_collection` (type: python, **forloop** over Step 1 output).
   - Map: `category ← item.category`, `subcategory ← item.subcategory`,
     `type ← item.type`, `handle ← item.handle`.
4. Step 3 → `f_insert_mongodb` (type: python).
   - Map all fields from Step 2 output.
5. Schedule the flow or run manually.

## Proxy & Rate Limiting

All HTTP requests in Steps 1 and 2 use:
- `requests.Session()` with proxy from `u/paluigi/vps3_proxy`
- Random delay of **0.8–1.5s** between every request (`random.randint(8, 15) / 10`)
- Retry on transient HTTP errors (429, 502, 503, 504) with exponential backoff

## Local Testing

Each script can be tested locally without Windmill by setting environment variables:

```bash
export WMILL_PROXY="http://your-proxy:port"
export WMILL_MONGO_URI="mongodb://localhost:27017"

# Step 1
python -c "import sys; sys.path.insert(0,'windmill'); from f_discover_categories import main; print(len(main()))"

# Step 2 (test with one handle)
python -c "import sys; sys.path.insert(0,'windmill'); from f_scrape_collection import main; r=main('Women','Women\\'s Dresses','maxi-dresses','Maxi Dresses'); print(r['product_count'])"
```
