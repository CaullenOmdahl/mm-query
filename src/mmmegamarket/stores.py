"""Store location management for MM Mega Market"""

from typing import List, Optional, Dict
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class Store(BaseModel):
    """MM Mega Market store location"""

    code: str
    name: str
    region: Optional[str] = None  # "North", "Central", "South"

    def get_b2c_store_code(self) -> str:
        """Get B2C store code"""
        # Extract numeric code (e.g., "10010" from "b2c_10010_vi")
        numeric_code = self.code.replace("b2c_", "").replace("mm_", "").replace("_vi", "")
        return f"b2c_{numeric_code}_vi"

    def get_b2b_store_code(self) -> str:
        """Get B2B store code"""
        numeric_code = self.code.replace("b2c_", "").replace("mm_", "").replace("_vi", "")
        return f"mm_{numeric_code}_vi"


class StoreManager:
    """Manage store locations"""

    STORE_LIST_QUERY = """
    query StoreList {
      storeList {
        name
        code
      }
    }
    """

    # Predefined store locations (from MM Mega Market website)
    KNOWN_STORES = {
        "10010": Store(code="10010", name="MM Mega Market An Phú", region="South"),
        "10015": Store(code="10015", name="MM Mega Market Bình Phú", region="South"),
        "10020": Store(code="10020", name="MM Mega Market Bình Tân", region="South"),
        "10035": Store(code="10035", name="MM Mega Market Thủ Đức", region="South"),
        # Add more stores as discovered
    }

    def __init__(self, api_client=None):
        self.api_client = api_client
        self.current_store: Optional[Store] = self.KNOWN_STORES.get("10010")  # Default to An Phú

    def list_stores(self) -> List[Store]:
        """
        List all available stores

        If API client is available, fetch from API.
        Otherwise, return known stores.
        """

        if self.api_client:
            try:
                # Try to fetch from B2C API
                result = self.api_client._execute_query(
                    "b2c",
                    self.STORE_LIST_QUERY,
                    {},
                    "StoreList"
                )

                if result and "data" in result and "storeList" in result["data"]:
                    stores = []
                    for store_data in result["data"]["storeList"]:
                        stores.append(
                            Store(
                                code=store_data["code"],
                                name=store_data["name"]
                            )
                        )
                    return stores

            except Exception as e:
                logger.warning(f"Failed to fetch stores from API: {e}")

        # Fallback to known stores
        return list(self.KNOWN_STORES.values())

    def get_store(self, store_code: str) -> Optional[Store]:
        """
        Get store by code

        Args:
            store_code: Store code (e.g., "10010", "b2c_10010_vi", or "mm_10010_vi")

        Returns:
            Store or None
        """

        # Extract numeric code
        numeric_code = store_code.replace("b2c_", "").replace("mm_", "").replace("_vi", "")

        return self.KNOWN_STORES.get(numeric_code)

    def set_current_store(self, store_code: str) -> bool:
        """
        Set the current active store

        Args:
            store_code: Store code

        Returns:
            bool: True if successful
        """

        store = self.get_store(store_code)

        if store:
            self.current_store = store
            logger.info(f"Current store set to: {store.name} ({store.code})")
            return True

        logger.error(f"Store not found: {store_code}")
        return False

    def get_current_store(self) -> Optional[Store]:
        """Get currently selected store"""
        return self.current_store

    def update_config_store(self, config, store_code: str) -> bool:
        """
        Update MMConfig with new store codes

        Args:
            config: MMConfig instance
            store_code: Store code to set

        Returns:
            bool: True if successful
        """

        store = self.get_store(store_code)

        if not store:
            return False

        # Update both B2C and B2B store codes
        config.b2c.store_code = store.get_b2c_store_code()
        config.b2b.store_code = store.get_b2b_store_code()

        logger.info(f"Config updated: B2C={config.b2c.store_code}, B2B={config.b2b.store_code}")

        return True

    @staticmethod
    def get_stores_by_region(region: str) -> List[Store]:
        """
        Get stores by region

        Args:
            region: "North", "Central", or "South"

        Returns:
            List of stores in that region
        """

        return [
            store for store in StoreManager.KNOWN_STORES.values()
            if store.region and store.region.lower() == region.lower()
        ]
