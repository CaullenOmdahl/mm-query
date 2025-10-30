"""MCP Server for MM Mega Market Vietnam"""

import logging
import json
from typing import Optional, Dict, Any, List
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .config import MMConfig
from .api_client import MMAPIClient
from .stores import StoreManager
from .models import Product, SearchResult, PriceComparison

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize server
app = Server("mmmegamarket")

# Initialize components
config = MMConfig.from_env()
api_client = MMAPIClient(config)
store_manager = StoreManager(api_client)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_products",
            description="Search for products on MM (B2C or B2B platform). Note: Product names and descriptions are in Vietnamese.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Product search keyword in English or Vietnamese (e.g., 'rice'/'gạo', 'milk'/'sữa', 'coffee'/'cà phê')"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["b2c", "b2b", "both"],
                        "default": "b2c",
                        "description": "Platform to search: 'b2c' (consumer), 'b2b' (business), or 'both'"
                    },
                    "page": {
                        "type": "integer",
                        "default": 1,
                        "description": "Page number for pagination"
                    },
                    "page_size": {
                        "type": "integer",
                        "default": 24,
                        "description": "Number of results per page (max 50)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["relevance", "price_asc", "price_desc", "name_asc", "name_desc"],
                        "default": "relevance",
                        "description": "Sort order for results"
                    }
                },
                "required": ["search_term"]
            }
        ),
        Tool(
            name="compare_prices",
            description="Compare prices between B2C (retail) and B2B (wholesale) platforms. Note: Product names are in Vietnamese.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Product search keyword in English or Vietnamese"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of products to compare"
                    }
                },
                "required": ["search_term"]
            }
        ),
        Tool(
            name="list_stores",
            description="List all available MM store locations",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["north", "central", "south", "all"],
                        "default": "all",
                        "description": "Filter stores by region"
                    }
                }
            }
        ),
        Tool(
            name="set_store",
            description="Set the active store location for searches",
            inputSchema={
                "type": "object",
                "properties": {
                    "store_code": {
                        "type": "string",
                        "description": "Store code (e.g., '10010' for An Phú)"
                    }
                },
                "required": ["store_code"]
            }
        ),
        Tool(
            name="get_current_store",
            description="Get the currently active store location",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="authenticate_b2b",
            description="Authenticate with B2B platform (required for B2B searches)",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "B2B account email (optional if set in environment)"
                    },
                    "password": {
                        "type": "string",
                        "description": "B2B account password (optional if set in environment)"
                    }
                }
            }
        ),
        Tool(
            name="get_auth_status",
            description="Check B2B authentication status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_product_details",
            description="Get detailed information about a specific product. Note: Product information is in Vietnamese.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Product SKU"
                    },
                    "platform": {
                        "type": "string",
                        "enum": ["b2c", "b2b"],
                        "default": "b2c",
                        "description": "Platform to query"
                    }
                },
                "required": ["sku"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""

    try:
        if name == "search_products":
            return await handle_search_products(arguments)

        elif name == "compare_prices":
            return await handle_compare_prices(arguments)

        elif name == "list_stores":
            return await handle_list_stores(arguments)

        elif name == "set_store":
            return await handle_set_store(arguments)

        elif name == "get_current_store":
            return await handle_get_current_store(arguments)

        elif name == "authenticate_b2b":
            return await handle_authenticate_b2b(arguments)

        elif name == "get_auth_status":
            return await handle_get_auth_status(arguments)

        elif name == "get_product_details":
            return await handle_get_product_details(arguments)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_search_products(args: dict) -> list[TextContent]:
    """Handle product search"""

    search_term = args["search_term"]
    platform = args.get("platform", "b2c")
    page = args.get("page", 1)
    page_size = min(args.get("page_size", 24), 50)
    sort_by = args.get("sort_by", "relevance")

    if platform == "both":
        # Search on both platforms
        b2c_result = api_client.search_products(search_term, "b2c", page, page_size, sort_by)
        b2b_result = api_client.search_products(search_term, "b2b", page, page_size, sort_by)

        response = f"# Search Results for '{search_term}'\n\n"

        if b2c_result:
            response += f"## B2C (Retail) - {b2c_result.total_count} products\n\n"
            response += format_products(b2c_result.products[:5])

        if b2b_result:
            response += f"\n## B2B (Wholesale) - {b2b_result.total_count} products\n\n"
            response += format_products(b2b_result.products[:5])

        return [TextContent(type="text", text=response)]

    else:
        result = api_client.search_products(search_term, platform, page, page_size, sort_by)

        if not result:
            return [TextContent(type="text", text=f"No results found or error occurred")]

        platform_name = "B2C (Retail)" if platform == "b2c" else "B2B (Wholesale)"

        response = f"# {platform_name} Search Results for '{search_term}'\n\n"
        response += f"**Total:** {result.total_count} products | **Page:** {page}/{result.total_pages}\n\n"
        response += format_products(result.products)

        return [TextContent(type="text", text=response)]


async def handle_compare_prices(args: dict) -> list[TextContent]:
    """Handle price comparison"""

    search_term = args["search_term"]
    max_results = args.get("max_results", 20)

    comparisons = api_client.compare_prices(search_term, max_results)

    if not comparisons:
        return [TextContent(type="text", text="No matching products found for comparison")]

    response = f"# Price Comparison for '{search_term}'\n\n"
    response += f"Comparing {len(comparisons)} products between B2C (retail) and B2B (wholesale)\n\n"

    for i, comp in enumerate(comparisons[:10], 1):
        response += f"## {i}. {comp.name}\n"
        response += f"- **SKU:** {comp.sku}\n"
        response += f"- **B2C Price:** {comp.b2c_price:,.0f} VND\n"
        response += f"- **B2B Price:** {comp.b2b_price:,.0f} VND\n"

        if comp.difference > 0:
            response += f"- **Savings:** {comp.difference:,.0f} VND ({comp.savings_percentage:.1f}% cheaper on B2B) ✓\n"
        elif comp.difference < 0:
            response += f"- **Difference:** {abs(comp.difference):,.0f} VND ({abs(comp.savings_percentage):.1f}% more expensive on B2B)\n"
        else:
            response += f"- **Same price on both platforms**\n"

        response += f"- [B2C Link]({comp.b2c_url}) | [B2B Link]({comp.b2b_url})\n\n"

    total_savings = sum(c.difference for c in comparisons if c.difference > 0)
    avg_savings = sum(c.savings_percentage for c in comparisons if c.difference > 0) / len([c for c in comparisons if c.difference > 0]) if comparisons else 0

    response += f"\n**Summary:**\n"
    response += f"- Products cheaper on B2B: {len([c for c in comparisons if c.difference > 0])}\n"
    response += f"- Average B2B savings: {avg_savings:.1f}%\n"
    response += f"- Total potential savings: {total_savings:,.0f} VND\n"

    return [TextContent(type="text", text=response)]


async def handle_list_stores(args: dict) -> list[TextContent]:
    """Handle store listing"""

    region = args.get("region", "all").lower()

    if region == "all":
        stores = store_manager.list_stores()
    else:
        stores = store_manager.get_stores_by_region(region)

    response = f"# MM Mega Market Store Locations\n\n"

    if not stores:
        response += "No stores found.\n"
    else:
        for store in stores:
            response += f"- **{store.name}**\n"
            response += f"  - Code: `{store.code}`\n"
            response += f"  - Region: {store.region or 'Unknown'}\n"
            response += f"  - B2C Store Code: `{store.get_b2c_store_code()}`\n"
            response += f"  - B2B Store Code: `{store.get_b2b_store_code()}`\n\n"

    return [TextContent(type="text", text=response)]


async def handle_set_store(args: dict) -> list[TextContent]:
    """Handle setting active store"""

    store_code = args["store_code"]

    success = store_manager.update_config_store(config, store_code)

    if success:
        store = store_manager.get_store(store_code)
        response = f"✓ Store set to: **{store.name}** ({store.code})\n"
        response += f"- B2C Store Code: `{config.b2c.store_code}`\n"
        response += f"- B2B Store Code: `{config.b2b.store_code}`\n"
    else:
        response = f"✗ Store not found: {store_code}\n"
        response += "Use `list_stores` to see available stores."

    return [TextContent(type="text", text=response)]


async def handle_get_current_store(args: dict) -> list[TextContent]:
    """Handle getting current store"""

    store = store_manager.get_current_store()

    if store:
        response = f"# Current Store\n\n"
        response += f"**{store.name}**\n"
        response += f"- Code: `{store.code}`\n"
        response += f"- Region: {store.region or 'Unknown'}\n"
        response += f"- B2C Store Code: `{config.b2c.store_code}`\n"
        response += f"- B2B Store Code: `{config.b2b.store_code}`\n"
    else:
        response = "No store selected."

    return [TextContent(type="text", text=response)]


async def handle_authenticate_b2b(args: dict) -> list[TextContent]:
    """Handle B2B authentication"""

    username = args.get("username")
    password = args.get("password")

    success = api_client.authenticate_b2b(username, password)

    if success:
        response = "✓ B2B authentication successful!\n"
        response += "You can now search products on the B2B platform."
    else:
        response = "✗ B2B authentication failed.\n"
        response += "Please check your credentials."

    return [TextContent(type="text", text=response)]


async def handle_get_auth_status(args: dict) -> list[TextContent]:
    """Handle getting auth status"""

    is_authenticated = api_client.is_b2b_authenticated()

    response = f"# B2B Authentication Status\n\n"

    if is_authenticated:
        response += "✓ **Authenticated** - You can access B2B pricing\n"
    else:
        response += "✗ **Not Authenticated** - B2B searches will fail\n"
        response += "\nUse `authenticate_b2b` to log in."

    return [TextContent(type="text", text=response)]


async def handle_get_product_details(args: dict) -> list[TextContent]:
    """Handle getting product details"""

    sku = args["sku"]
    platform = args.get("platform", "b2c")

    # Search by SKU
    result = api_client.search_products(sku, platform, page_size=10)

    if not result or not result.products:
        return [TextContent(type="text", text=f"Product not found: {sku}")]

    # Find exact SKU match
    product = next((p for p in result.products if p.sku == sku), result.products[0])

    response = f"# {product.name}\n\n"
    response += f"- **SKU:** {product.sku}\n"
    response += f"- **Product ID:** {product.id}\n"
    response += f"- **Price:** {product.price:,.0f} {product.price_range.final_price.currency}\n"

    if product.price_range.has_discount:
        response += f"- **Regular Price:** {product.regular_price:,.0f} VND\n"
        response += f"- **Discount:** {product.price_range.discount_amount:,.0f} VND ({product.price_range.discount_percentage:.1f}% off)\n"

    response += f"- **Stock:** {product.stock_status} {'✓' if product.is_in_stock else '✗'}\n"
    response += f"- **Platform:** {product.platform.upper()}\n"

    if product.categories:
        response += f"- **Categories:** {', '.join(cat.name for cat in product.categories)}\n"

    if product.rating_summary:
        response += f"- **Rating:** {product.rating_summary}/100\n"

    response += f"- **URL:** {product.full_url}\n"

    if product.small_image_url:
        response += f"- **Image:** {product.small_image_url}\n"

    return [TextContent(type="text", text=response)]


def format_products(products: List[Product]) -> str:
    """Format product list for output"""

    output = ""

    for i, product in enumerate(products, 1):
        output += f"### {i}. {product.name}\n"
        output += f"- **Price:** {product.price:,.0f} VND"

        if product.price_range.has_discount:
            output += f" ~~{product.regular_price:,.0f} VND~~ (-{product.price_range.discount_percentage:.0f}%)"

        output += f"\n- **SKU:** {product.sku}\n"
        output += f"- **Stock:** {product.stock_status}\n"
        output += f"- [View Product]({product.full_url})\n\n"

    return output


def main():
    """Run the MCP server"""
    import asyncio
    from mcp.server.stdio import stdio_server

    logger.info("Starting MM Mega Market MCP Server...")
    logger.info("Note: B2B authentication is optional for product browsing")

    # Auto-authenticate B2B if credentials are available (optional)
    if config.b2b_auth.username and config.b2b_auth.password:
        logger.info("B2B credentials found, authentication available if needed")
        # Don't authenticate automatically - it's not needed for basic searches
        # Users can call authenticate_b2b tool if they need account-specific features

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
