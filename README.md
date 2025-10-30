# MM Query - MCP Server

Query products from MM's retail (B2C) and wholesale (B2B) platforms using the Model Context Protocol.

## Features

- 🔍 Search products across B2C and B2B platforms
- 💰 Compare retail vs wholesale prices
- 📦 Check stock availability
- 🏪 Multi-store support
- 🔗 Direct product links
- 🌐 Vietnamese language support

## Installation

### Via Smithery (Recommended)

```bash
smithery install mmmegamarket-mcp
```

### Via uvx

```bash
uvx mmmegamarket-mcp
```

### Via pip

```bash
pip install mmmegamarket-mcp
```

## Configuration

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mm-query": {
      "command": "uvx",
      "args": ["mmmegamarket-mcp"],
      "env": {
        "MMPRO_USERNAME": "your_b2b_email@example.com",
        "MMPRO_PASSWORD": "your_b2b_password"
      }
    }
  }
}
```

**Note:** B2B credentials are optional. B2C (retail) features work without authentication.

## Available Tools

### 1. search_products
Search for products on MM.

**Note:** Product names and descriptions are in Vietnamese.

**Parameters:**
- `search_term` - Keyword in English or Vietnamese (e.g., 'rice'/'gạo', 'milk'/'sữa')
- `platform` - "b2c", "b2b", or "both" (default: "b2c")
- `page` - Page number (default: 1)
- `page_size` - Results per page, max 50 (default: 24)
- `sort_by` - Sort order: "relevance", "price_asc", "price_desc", etc.

### 2. compare_prices
Compare prices between B2C (retail) and B2B (wholesale) platforms.

**Parameters:**
- `search_term` - Product keyword
- `max_results` - Maximum products to compare (default: 20)

### 3. list_stores
List all MM store locations.

**Parameters:**
- `region` - "north", "central", "south", or "all" (default: "all")

### 4. set_store
Set the active store location for searches.

**Parameters:**
- `store_code` - Store code (e.g., '10010')

### 5. get_current_store
Get the currently active store location.

### 6. authenticate_b2b
Authenticate with B2B platform (optional).

**Parameters:**
- `username` - B2B account email
- `password` - B2B account password

### 7. get_auth_status
Check B2B authentication status.

### 8. get_product_details
Get detailed information about a specific product.

**Parameters:**
- `sku` - Product SKU
- `platform` - "b2c" or "b2b" (default: "b2c")

## Usage Examples

### Basic Product Search
```
Search for "coffee"
```

### Price Comparison
```
Compare prices for "cooking oil" between B2C and B2B
```

### Multi-Platform Search
```
Search for "rice" on both B2C and B2B platforms
```

### Store Selection
```
List stores in south region
Set store to 10010
Search for "milk"
```

## Language Note

The database is primarily in Vietnamese. Product names, descriptions, and categories will be in Vietnamese. Search terms can be provided in either English or Vietnamese.

## Platforms

### B2C Platform
- Consumer/retail platform
- Retail pricing
- No authentication required

### B2B Platform
- Business/wholesale platform
- Wholesale pricing (typically 5-15% cheaper)
- Optional authentication for full features

## PyPI Package

This MCP server is published as `mmmegamarket-mcp` on PyPI.

**Package URL:** https://pypi.org/project/mmmegamarket-mcp/

## License

MIT License

## Support

- **Issues:** https://github.com/CaullenOmdahl/mm-query/issues
- **PyPI:** https://pypi.org/project/mmmegamarket-mcp/
