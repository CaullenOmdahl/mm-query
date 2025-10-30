"""Configuration management for MM Mega Market MCP Server"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class PlatformConfig(BaseModel):
    """Configuration for a specific platform (B2C or B2B)"""

    name: str
    endpoint: str
    store_code: str
    requires_auth: bool = False


class AuthConfig(BaseModel):
    """Authentication configuration"""

    username: Optional[str] = None
    password: Optional[str] = None
    customer_token: Optional[str] = None


class MMConfig(BaseModel):
    """Main configuration for MM Mega Market MCP Server"""

    # B2C Platform (Consumer)
    b2c: PlatformConfig = Field(
        default=PlatformConfig(
            name="online.mmvietnam.com",
            endpoint="https://online.mmvietnam.com/graphql",
            store_code="b2c_10010_vi",
            requires_auth=False,
        )
    )

    # B2B Platform (Business)
    b2b: PlatformConfig = Field(
        default=PlatformConfig(
            name="mmpro.vn",
            endpoint="https://mmpro.vn/graphql",
            store_code="mm_10010_vi",
            requires_auth=True,
        )
    )

    # B2B Authentication (from environment or credentials)
    b2b_auth: AuthConfig = Field(
        default_factory=lambda: AuthConfig(
            username=os.getenv("MMPRO_USERNAME"),
            password=os.getenv("MMPRO_PASSWORD"),
            customer_token=os.getenv("MMPRO_CUSTOMER_TOKEN"),
        )
    )

    # API Settings
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    rate_limit_delay: float = Field(
        default=1.0, description="Delay between requests in seconds"
    )

    # User Agent - must look like a browser or mmpro.vn returns 403
    user_agent: str = Field(
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    @classmethod
    def from_env(cls) -> "MMConfig":
        """Create configuration from environment variables"""
        return cls()

    def set_b2b_credentials(self, username: str, password: str) -> None:
        """Set B2B authentication credentials"""
        self.b2b_auth.username = username
        self.b2b_auth.password = password

    def set_b2b_token(self, token: str) -> None:
        """Set B2B customer token directly"""
        self.b2b_auth.customer_token = token


# Global configuration instance
config = MMConfig.from_env()
