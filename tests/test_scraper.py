"""Tests for the shopzetu scraper."""

import pytest
import respx
import httpx
from shopzetu_scraper.categories import get_leaf_collections
from shopzetu_scraper.client import ShopzetuClient, API_PATH
from shopzetu_scraper.storage import _transform_product


# ──────────────────── categories.py ────────────────────


class TestCategories:
    def test_returns_non_empty_list(self):
        leaves = get_leaf_collections()
        assert len(leaves) > 0

    def test_each_leaf_has_required_keys(self):
        for leaf in get_leaf_collections():
            assert "category" in leaf
            assert "subcategory" in leaf
            assert "handle" in leaf
            assert "type" in leaf

    def test_all_top_categories_present(self):
        cats = {l["category"] for l in get_leaf_collections()}
        assert cats == {"Women", "Men", "Kids", "Activewear", "Beauty"}

    def test_cross_cutting_excluded(self):
        """Brands/Sale/Trending should NOT appear as categories."""
        cats = {l["category"] for l in get_leaf_collections()}
        assert "Brands" not in cats
        assert "Sale" not in cats
        assert "New In" not in cats

    def test_some_have_3_levels(self):
        """At least some leaves should have a type (3-level depth)."""
        three_level = [l for l in get_leaf_collections() if l["type"] is not None]
        assert len(three_level) > 10


# ──────────────────── client.py ────────────────────


SAMPLE_API_RESPONSE = {
    "products": [
        {
            "id": "gid://shopify/Product/123",
            "handle": "test-dress",
            "title": "Test Dress - Blue",
            "vendor": "TestBrand",
            "tags": ["DRESSES", "BLUE"],
            "createdAt": "2026-01-01T00:00:00Z",
            "priceRange": {
                "minVariantPrice": {"amount": "5000.0", "currencyCode": "KES"},
                "maxVariantPrice": {"amount": "5000.0", "currencyCode": "KES"},
            },
            "variants": {
                "nodes": [
                    {
                        "availableForSale": True,
                        "price": {"amount": "5000.0", "currencyCode": "KES"},
                        "compareAtPrice": None,
                        "selectedOptions": [
                            {"name": "Size", "value": "M"},
                        ],
                    }
                ]
            },
        }
    ],
    "pageInfo": {"hasNextPage": False, "endCursor": None},
}


class TestClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_page_returns_products(self):
        url = "https://www.shopzetu.com/api/collections/test-handle/products"
        respx.get(url).mock(return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE))

        async with ShopzetuClient(min_delay=0, max_delay=0) as client:
            data = await client.fetch_page("test-handle")

        assert len(data["products"]) == 1
        assert data["products"][0]["handle"] == "test-dress"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_all_paginates(self):
        url = "https://www.shopzetu.com/api/collections/h/products"

        # Page 1: hasNextPage=True, page 2: hasNextPage=False
        page1 = {**SAMPLE_API_RESPONSE, "pageInfo": {"hasNextPage": True, "endCursor": "abc"}}
        page2 = {**SAMPLE_API_RESPONSE, "pageInfo": {"hasNextPage": False, "endCursor": None}}

        route = respx.get(url)
        route.mock(side_effect=[httpx.Response(200, json=page1), httpx.Response(200, json=page2)])

        async with ShopzetuClient(min_delay=0, max_delay=0) as client:
            products = await client.fetch_all("h")

        assert len(products) == 2  # 1 from each page

    @respx.mock
    @pytest.mark.asyncio
    async def test_max_pages_limit(self):
        url = "https://www.shopzetu.com/api/collections/h/products"
        page = {**SAMPLE_API_RESPONSE, "pageInfo": {"hasNextPage": True, "endCursor": "abc"}}
        respx.get(url).mock(return_value=httpx.Response(200, json=page))

        async with ShopzetuClient(min_delay=0, max_delay=0) as client:
            products = await client.fetch_all("h", max_pages=1)

        assert len(products) == 1


# ──────────────────── storage.py ────────────────────


class TestTransformProduct:
    def test_basic_transform(self):
        doc = _transform_product(SAMPLE_API_RESPONSE["products"][0], "Women", "Dresses", "Maxi")
        assert doc["product_id"] == "gid://shopify/Product/123"
        assert doc["product_name"] == "Test Dress - Blue"
        assert doc["brand"] == "TestBrand"
        assert doc["price"] == "5000.0"
        assert doc["currency"] == "KES"
        assert doc["original_price"] is None  # no discount
        assert doc["product_url"] == "https://www.shopzetu.com/products/test-dress"
        assert doc["available_for_sale"] is True
        assert doc["tags"] == ["DRESSES", "BLUE"]

    def test_discounted_product(self):
        raw = {
            **SAMPLE_API_RESPONSE["products"][0],
            "variants": {
                "nodes": [
                    {
                        "availableForSale": True,
                        "price": {"amount": "4000.0", "currencyCode": "KES"},
                        "compareAtPrice": {"amount": "5000.0", "currencyCode": "KES"},
                        "selectedOptions": [],
                    }
                ]
            },
        }
        doc = _transform_product(raw, "Women", "Dresses", None)
        assert doc["price"] == "5000.0"  # from priceRange min
        assert doc["original_price"] == "5000.0"  # from compareAtPrice
        assert doc["original_currency"] == "KES"

    def test_category_path_attached(self):
        doc = _transform_product(SAMPLE_API_RESPONSE["products"][0], "Men", "Bottoms", None)
        assert doc["category_path"]["category"] == "Men"
        assert doc["category_path"]["subcategory"] == "Bottoms"
        assert doc["category_path"]["type"] is None
