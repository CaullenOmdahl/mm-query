"""Data models for MM Mega Market products and responses"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class Price(BaseModel):
    """Price information"""

    value: float
    currency: str = "VND"


class PriceRange(BaseModel):
    """Price range with regular and final prices"""

    final_price: Price
    regular_price: Price
    discount_amount: Optional[float] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.discount_amount is None:
            self.discount_amount = self.regular_price.value - self.final_price.value

    @property
    def has_discount(self) -> bool:
        return self.discount_amount > 0

    @property
    def discount_percentage(self) -> float:
        if self.regular_price.value > 0:
            return (self.discount_amount / self.regular_price.value) * 100
        return 0.0


class Category(BaseModel):
    """Product category"""

    uid: Optional[str] = None
    name: str


class Product(BaseModel):
    """Product information"""

    id: int
    uid: str
    name: str
    sku: str
    price_range: PriceRange
    stock_status: str
    url_key: str
    small_image_url: Optional[str] = None
    categories: List[Category] = Field(default_factory=list)
    rating_summary: Optional[float] = None

    # Platform information
    platform: Optional[str] = None  # "b2c" or "b2b"
    scraped_at: datetime = Field(default_factory=datetime.now)

    @property
    def full_url(self) -> str:
        """Get full product URL"""
        if self.platform == "b2c":
            return f"https://online.mmvietnam.com/{self.url_key}.html"
        elif self.platform == "b2b":
            return f"https://mmpro.vn/product/{self.url_key}.html"
        return f"/{self.url_key}.html"

    @property
    def price(self) -> float:
        """Get final price value"""
        return self.price_range.final_price.value

    @property
    def regular_price(self) -> float:
        """Get regular price value"""
        return self.price_range.regular_price.value

    @property
    def is_in_stock(self) -> bool:
        """Check if product is in stock"""
        return self.stock_status == "IN_STOCK"

    def to_dict(self) -> dict:
        """Convert to dictionary for export"""
        return {
            "id": self.id,
            "uid": self.uid,
            "name": self.name,
            "sku": self.sku,
            "price": self.price,
            "regular_price": self.regular_price,
            "discount_amount": self.price_range.discount_amount,
            "discount_percentage": self.price_range.discount_percentage,
            "currency": self.price_range.final_price.currency,
            "stock_status": self.stock_status,
            "in_stock": self.is_in_stock,
            "url": self.full_url,
            "image_url": self.small_image_url,
            "categories": [cat.name for cat in self.categories],
            "rating": self.rating_summary,
            "platform": self.platform,
            "scraped_at": self.scraped_at.isoformat(),
        }


class SearchResult(BaseModel):
    """Search result with products and pagination info"""

    products: List[Product]
    total_count: int
    total_pages: int
    current_page: int
    platform: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "products": [p.to_dict() for p in self.products],
            "total_count": self.total_count,
            "total_pages": self.total_pages,
            "current_page": self.current_page,
            "platform": self.platform,
        }


class PriceComparison(BaseModel):
    """Price comparison between B2C and B2B"""

    product_id: int
    sku: str
    name: str
    b2c_price: float
    b2b_price: float
    difference: float
    savings_percentage: float
    b2c_url: str
    b2b_url: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "product_id": self.product_id,
            "sku": self.sku,
            "name": self.name,
            "b2c_price": self.b2c_price,
            "b2b_price": self.b2b_price,
            "difference": self.difference,
            "savings_percentage": self.savings_percentage,
            "better_deal": "B2B" if self.difference > 0 else "B2C",
            "b2c_url": self.b2c_url,
            "b2b_url": self.b2b_url,
        }


class AuthResponse(BaseModel):
    """Authentication response"""

    token: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
