"""HTTP client for the shopzetu.com hidden API.

The site is a Shopify Hydrogen (React/Remix) headless storefront. Product data
is fetched internally via a JSON endpoint discovered in the client-side bundle::

    GET /api/collections/{handle}/products?first=250&cursor={cursor}

No authentication required.  Cursor-based pagination with up to 250 items per page.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.shopzetu.com"
API_PATH = "/api/collections/{handle}/products"
DEFAULT_PAGE_SIZE = 250
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class APIError(Exception):
    """Raised when the API returns an unexpected response."""


@dataclass
class ShopzetuClient:
    """Thin async/await client around the shopzetu JSON API.

    Adds random delays between requests and automatic retry on transient failures.
    """

    base_url: str = BASE_URL
    page_size: int = DEFAULT_PAGE_SIZE
    min_delay: float = 1.0
    max_delay: float = 3.0
    max_retries: int = 3
    retry_backoff: float = 2.0
    timeout: float = 30.0
    _client: httpx.AsyncClient | None = field(default=None, init=False)

    async def __aenter__(self) -> ShopzetuClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch_page(
        self,
        handle: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Fetch a single page of products for *handle*.

        Returns the raw JSON dict with ``products`` (list) and ``pageInfo``
        (``hasNextPage``, ``endCursor``).
        """
        if self._client is None:
            raise RuntimeError("Client not started. Use 'async with ShopzetuClient() as c:'")

        params: dict[str, str] = {"first": str(self.page_size)}
        if cursor:
            params["cursor"] = cursor

        url = API_PATH.format(handle=handle)
        query = urlencode(params)

        for attempt in range(1, self.max_retries + 1):
            # Random delay before every request (including retries)
            delay = random.uniform(self.min_delay, self.max_delay)
            logger.debug("Sleeping %.2fs before request", delay)
            await _sleep(delay)

            try:
                resp = await self._client.get(f"{url}?{query}")
            except httpx.HTTPError as exc:
                logger.warning("HTTP error (attempt %d/%d): %s", attempt, self.max_retries, exc)
                if attempt == self.max_retries:
                    raise APIError(f"Request failed after {self.max_retries} retries: {exc}") from exc
                await _sleep(self.retry_backoff**attempt)
                continue

            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception as exc:
                    raise APIError(f"Invalid JSON from {url}: {exc}") from exc

            if resp.status_code in (429, 502, 503, 504):
                wait = self.retry_backoff**attempt
                logger.warning(
                    "Transient %d (attempt %d/%d) — retrying in %.1fs",
                    resp.status_code,
                    attempt,
                    self.max_retries,
                    wait,
                )
                await _sleep(wait)
                continue

            raise APIError(f"HTTP {resp.status_code} from {url}: {resp.text[:200]}")

        raise APIError(f"Exhausted retries for {url}")  # unreachable

    async def fetch_all(
        self,
        handle: str,
        *,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Paginate through *all* products in a collection.

        If *max_pages* is given, stop early (useful for testing).
        """
        all_products: list[dict[str, Any]] = []
        cursor: str | None = None
        page = 0

        while True:
            page += 1
            data = await self.fetch_page(handle, cursor=cursor)
            products = data.get("products", [])
            all_products.extend(products)

            page_info = data.get("pageInfo", {})
            logger.info(
                "[%s] page %d: +%d products (total %d)",
                handle,
                page,
                len(products),
                len(all_products),
            )

            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

            if max_pages and page >= max_pages:
                logger.info("[%s] reached max_pages=%d, stopping", handle, max_pages)
                break

        return all_products


async def _sleep(seconds: float) -> None:
    """Indirection for testability."""
    await __import__("asyncio").sleep(seconds)
