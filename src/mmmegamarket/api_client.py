"""Core API client for MM Mega Market platforms"""

import requests
import time
import json
import logging
from typing import List, Optional, Dict, Any, Literal

from .config import MMConfig
from .auth import MMAuthClient
from .models import Product, SearchResult, PriceComparison, Price, PriceRange, Category

logger = logging.getLogger(__name__)

PlatformType = Literal["b2c", "b2b"]


class MMAPIClient:
    """API Client for MM Mega Market (B2C and B2B)"""

    # Simpler query that works without authentication
    PRODUCT_SEARCH_QUERY = """
query ProductSearch($currentPage: Int, $inputText: String!, $pageSize: Int) {
  products(currentPage: $currentPage, pageSize: $pageSize, search: $inputText) {
    items {
      id
      uid
      name
      sku
      price_range {
        maximum_price {
          final_price { currency value }
          regular_price { currency value }
        }
      }
      small_image { url }
      stock_status
      url_key
      categories { uid name }
    }
    total_count
    page_info { total_pages }
  }
}
"""

    def __init__(self, config: Optional[MMConfig] = None):
        self.config = config or MMConfig.from_env()
        self.auth_client = MMAuthClient(self.config)
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            time.sleep(self.config.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _execute_query(
        self,
        platform: PlatformType,
        query: str,
        variables: Dict[str, Any],
        operation_name: str,
    ) -> Optional[Dict]:
        """Execute a GraphQL query on specified platform"""

        self._rate_limit()

        endpoint = self.config.b2c.endpoint if platform == "b2c" else self.config.b2b.endpoint

        headers = (
            self.auth_client.get_b2c_headers()
            if platform == "b2c"
            else self.auth_client.get_b2b_headers()
        )

        # Use GET with query parameters (as observed in HAR files)
        params = {
            "query": query,
            "operationName": operation_name,
            "variables": json.dumps(variables)
        }

        for attempt in range(self.config.retry_attempts):
            try:
                logger.debug(
                    f"Executing {operation_name} on {platform} (attempt {attempt + 1})"
                )

                response = requests.get(
                    endpoint, params=params, headers=headers, timeout=self.config.timeout
                )

                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    # If B2B auth error, try to re-authenticate
                    if platform == "b2b" and any(
                        "authorization" in str(err).lower() for err in data["errors"]
                    ):
                        logger.info("B2B authentication expired, re-authenticating...")
                        if self.auth_client.authenticate_b2b():
                            headers = self.auth_client.get_b2b_headers()
                            continue
                    return None

                return data

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None

        return None

    def _parse_product(self, item: Dict, platform: PlatformType) -> Product:
        """Parse product data from API response"""

        price_info = item["price_range"]["maximum_price"]

        return Product(
            id=item["id"],
            uid=item["uid"],
            name=item["name"],
            sku=item["sku"],
            price_range=PriceRange(
                final_price=Price(
                    value=price_info["final_price"]["value"],
                    currency=price_info["final_price"]["currency"],
                ),
                regular_price=Price(
                    value=price_info["regular_price"]["value"],
                    currency=price_info["regular_price"]["currency"],
                ),
            ),
            stock_status=item["stock_status"],
            url_key=item["url_key"],
            small_image_url=item.get("small_image", {}).get("url"),
            categories=[
                Category(uid=cat.get("uid"), name=cat["name"])
                for cat in item.get("categories", [])
            ],
            rating_summary=item.get("rating_summary"),
            platform=platform,
        )

    def search_products(
        self,
        search_term: str,
        platform: PlatformType = "b2c",
        page: int = 1,
        page_size: int = 24,
        sort_by: str = "relevance",
    ) -> Optional[SearchResult]:
        """
        Search for products on specified platform

        Args:
            search_term: Search keyword
            platform: "b2c" or "b2b"
            page: Page number (default: 1)
            page_size: Results per page (default: 24)
            sort_by: Sort order - "relevance", "price_asc", "price_desc", "name_asc", "name_desc"

        Returns:
            SearchResult or None
        """

        # B2B authentication is optional - product browsing works without it
        # Authentication is only needed for customer-specific features (cart, wishlist, etc.)
        if platform == "b2b" and not self.auth_client.is_b2b_authenticated():
            logger.debug("B2B search without authentication (using public pricing)")

        # Simple variables - no filters or sort for unauthenticated access
        variables = {
            "currentPage": page,
            "pageSize": page_size,
            "inputText": search_term,
        }

        result = self._execute_query(platform, self.PRODUCT_SEARCH_QUERY, variables, "ProductSearch")

        if not result or "data" not in result or "products" not in result["data"]:
            return None

        products_data = result["data"]["products"]

        products = [self._parse_product(item, platform) for item in products_data["items"]]

        return SearchResult(
            products=products,
            total_count=products_data["total_count"],
            total_pages=products_data["page_info"]["total_pages"],
            current_page=page,
            platform=platform,
        )

    def search_all_pages(
        self,
        search_term: str,
        platform: PlatformType = "b2c",
        max_pages: Optional[int] = None,
    ) -> List[Product]:
        """
        Search for products across all pages

        Args:
            search_term: Search keyword
            platform: "b2c" or "b2b"
            max_pages: Maximum number of pages to fetch (None for all)

        Returns:
            List of all products
        """

        all_products = []
        page = 1

        while True:
            result = self.search_products(search_term, platform, page=page, page_size=50)

            if not result or not result.products:
                break

            all_products.extend(result.products)

            logger.info(
                f"Fetched page {page}/{result.total_pages} - "
                f"{len(result.products)} products "
                f"(total: {len(all_products)}/{result.total_count})"
            )

            if max_pages and page >= max_pages:
                break

            if page >= result.total_pages:
                break

            page += 1

        return all_products

    def compare_prices(
        self, search_term: str, max_results: int = 20
    ) -> List[PriceComparison]:
        """
        Compare prices between B2C and B2B platforms

        Args:
            search_term: Search keyword
            max_results: Maximum number of results to compare

        Returns:
            List of price comparisons
        """

        # Search on both platforms
        b2c_result = self.search_products(search_term, "b2c", page_size=max_results)
        b2b_result = self.search_products(search_term, "b2b", page_size=max_results)

        if not b2c_result or not b2b_result:
            logger.error("Failed to fetch data from one or both platforms")
            return []

        # Create SKU lookup for B2B products
        b2b_by_sku = {p.sku: p for p in b2b_result.products}

        comparisons = []

        for b2c_product in b2c_result.products:
            b2b_product = b2b_by_sku.get(b2c_product.sku)

            if not b2b_product:
                continue

            difference = b2c_product.price - b2b_product.price
            savings_pct = (difference / b2c_product.price) * 100 if b2c_product.price > 0 else 0

            comparisons.append(
                PriceComparison(
                    product_id=b2c_product.id,
                    sku=b2c_product.sku,
                    name=b2c_product.name,
                    b2c_price=b2c_product.price,
                    b2b_price=b2b_product.price,
                    difference=difference,
                    savings_percentage=savings_pct,
                    b2c_url=b2c_product.full_url,
                    b2b_url=b2b_product.full_url,
                )
            )

        # Sort by savings percentage (highest first)
        comparisons.sort(key=lambda x: x.savings_percentage, reverse=True)

        return comparisons

    def authenticate_b2b(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with B2B platform

        Args:
            username: B2B account username (optional if in config)
            password: B2B account password (optional if in config)

        Returns:
            bool: True if successful
        """
        return self.auth_client.authenticate_b2b(username, password)

    def is_b2b_authenticated(self) -> bool:
        """Check if B2B authentication is active"""
        return self.auth_client.is_b2b_authenticated()
