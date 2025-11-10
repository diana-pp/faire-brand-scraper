thonimport logging
from typing import Any, Dict, Optional

import requests

from .brand_parser import BrandParser

logger = logging.getLogger(__name__)

class ProductExtractor:
    """
    Fetch product-related metadata for a brand.

    Like BrandParser, this class is defensive: if anything goes wrong,
    we log it and return an empty structure rather than raising.
    """

    def __init__(self, session: requests.Session, base_url: str, timeout: float = 10.0):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_product_stats(self, identifier: str) -> Dict[str, Any]:
        """
        Retrieve aggregate product metrics for a given brand.

        Returns a dictionary with keys like:
        - active_products_count
        - lead_time_days
        - last_product_added_at
        """
        token = BrandParser.extract_token(identifier)
        url = f"{self.base_url}/brands/{token}/products"

        logger.debug("Fetching product data for brand '%s' from %s", token, url)

        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            logger.warning(
                "Network error while fetching products for brand %s: %s", token, e
            )
            return {}

        if not resp.ok:
            logger.warning(
                "Non-success status code %s while fetching products for brand %s",
                resp.status_code,
                token,
            )
            return {}

        try:
            payload = resp.json()
        except ValueError:
            logger.warning(
                "Response for products of brand %s is not JSON; ignoring.", token
            )
            return {}

        products = self._extract_products(payload)
        active_count = self._count_active_products(products)
        lead_time_days = self._average_lead_time_days(products)
        last_added_at = self._last_added_at(products)

        result: Dict[str, Any] = {}
        if active_count is not None:
            result["active_products_count"] = active_count
        if lead_time_days is not None:
            result["lead_time_days"] = lead_time_days
        if last_added_at is not None:
            result["last_product_added_at"] = last_added_at

        return result

    @staticmethod
    def _extract_products(payload: Any) -> list:
        """
        Normalize various payload shapes to a simple list of products.
        """
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            if "products" in payload and isinstance(payload["products"], list):
                return payload["products"]
            # Sometimes under "data" or similar
            if "data" in payload and isinstance(payload["data"], list):
                return payload["data"]

        return []

    @staticmethod
    def _count_active_products(products: list) -> Optional[int]:
        if not products:
            return None
        try:
            return sum(1 for p in products if p.get("active", True))
        except Exception:
            return None

    @staticmethod
    def _average_lead_time_days(products: list) -> Optional[int]:
        """
        Compute the average lead time in days across products that declare it.
        """
        if not products:
            return None

        values = []
        for p in products:
            shipping = p.get("shipping") or {}
            lead_time = shipping.get("lead_time_days") or p.get("lead_time_days")
            if lead_time is None:
                continue
            try:
                values.append(int(lead_time))
            except (TypeError, ValueError):
                continue

        if not values:
            return None

        return int(round(sum(values) / len(values)))

    @staticmethod
    def _last_added_at(products: list) -> Optional[str]:
        """
        Return the most recent 'created_at' timestamp from products, if available.
        """
        latest: Optional[str] = None
        for p in products:
            created_at = p.get("created_at")
            if not created_at:
                continue
            if latest is None or created_at > latest:
                latest = created_at
        return latest