"""Authentication module for MM Mega Market B2B platform"""

import requests
from typing import Optional
import logging

from .models import AuthResponse
from .config import MMConfig, AuthConfig

logger = logging.getLogger(__name__)


class MMAuthClient:
    """Authentication client for MM Mega Market platforms"""

    def __init__(self, config: MMConfig):
        self.config = config
        self.b2b_token: Optional[str] = None

        # Use existing token if available
        if config.b2b_auth.customer_token:
            self.b2b_token = config.b2b_auth.customer_token
            logger.info("Using existing B2B customer token")

    def authenticate_b2b(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with B2B platform and obtain customer token

        GraphQL mutation for customer authentication:
        mutation {
          generateCustomerToken(email: "user@example.com", password: "password") {
            token
          }
        }

        Args:
            username: B2B account username/email (optional if in config)
            password: B2B account password (optional if in config)

        Returns:
            bool: True if authentication successful
        """
        # Use provided credentials or fall back to config
        email = username or self.config.b2b_auth.username
        pwd = password or self.config.b2b_auth.password

        if not email or not pwd:
            logger.error("B2B credentials not provided")
            return False

        mutation = """
        mutation generateCustomerToken($email: String!, $password: String!) {
          generateCustomerToken(email: $email, password: $password) {
            token
          }
        }
        """

        variables = {"email": email, "password": pwd}

        headers = {
            "Content-Type": "application/json",
            "store": self.config.b2b.store_code,
            "User-Agent": self.config.user_agent,
        }

        payload = {
            "query": mutation,
            "operationName": "generateCustomerToken",
            "variables": variables,
        }

        try:
            logger.info(f"Authenticating with B2B platform as {email}")
            response = requests.post(
                self.config.b2b.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error(f"B2B authentication failed: {data['errors']}")
                return False

            if "data" in data and "generateCustomerToken" in data["data"]:
                token_data = data["data"]["generateCustomerToken"]
                self.b2b_token = token_data["token"]
                self.config.b2b_auth.customer_token = self.b2b_token
                logger.info("B2B authentication successful")
                return True

            logger.error("Unexpected authentication response format")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"B2B authentication error: {e}")
            return False

    def get_b2b_headers(self) -> dict:
        """Get headers for authenticated B2B requests"""
        headers = {
            "Content-Type": "application/json",
            "store": self.config.b2b.store_code,
            "User-Agent": self.config.user_agent,
        }

        if self.b2b_token:
            headers["Authorization"] = f"Bearer {self.b2b_token}"

        return headers

    def get_b2c_headers(self) -> dict:
        """Get headers for B2C requests (no auth required)"""
        return {
            "Content-Type": "application/json",
            "store": self.config.b2c.store_code,
            "User-Agent": self.config.user_agent,
        }

    def is_b2b_authenticated(self) -> bool:
        """Check if B2B authentication is active"""
        return self.b2b_token is not None

    def verify_b2b_token(self) -> bool:
        """Verify that the B2B token is still valid"""
        if not self.b2b_token:
            return False

        # Query customer data to verify token
        query = """
        query {
          customer {
            email
            firstname
            lastname
          }
        }
        """

        headers = self.get_b2b_headers()
        payload = {"query": query}

        try:
            response = requests.post(
                self.config.b2b.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.warning("B2B token verification failed")
                return False

            if "data" in data and "customer" in data["data"]:
                logger.info(f"B2B token valid for {data['data']['customer'].get('email')}")
                return True

            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Token verification error: {e}")
            return False

    def logout_b2b(self) -> bool:
        """Logout from B2B platform"""
        if not self.b2b_token:
            return True

        mutation = """
        mutation {
          revokeCustomerToken {
            result
          }
        }
        """

        headers = self.get_b2b_headers()
        payload = {"query": mutation, "operationName": "revokeCustomerToken"}

        try:
            response = requests.post(
                self.config.b2b.endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "data" in data and data["data"].get("revokeCustomerToken", {}).get("result"):
                logger.info("B2B logout successful")
                self.b2b_token = None
                self.config.b2b_auth.customer_token = None
                return True

            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"B2B logout error: {e}")
            return False
