thonimport logging
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

import requests

from .utils_date import parse_date_iso

logger = logging.getLogger(__name__)

@dataclass
class BrandInfo:
    token: str
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    url: Optional[str] = None
    instagram_handle: Optional[str] = None
    country: Optional[str] = None
    made_in: Optional[str] = None
    active_products_count: Optional[int] = None
    lead_time_days: Optional[int] = None
    first_order_minimum_amount: Optional[float] = None
    accepted_terms: Optional[bool] = None
    eco_friendly: Optional[bool] = None
    women_owned: Optional[bool] = None
    sold_on_amazon: Optional[bool] = None
    badges: Optional[list] = None
    business_identifiers: Optional[list] = None
    story_images: Optional[list] = None
    video_url: Optional[str] = None
    brand_reviews_summary: Optional[Dict[str, Any]] = None
    vacation_start_date: Optional[str] = None
    vacation_end_date: Optional[str] = None
    vacation_banner_text: Optional[str] = None
    source_error: Optional[str] = None

class BrandParser:
    """
    High-level wrapper around Faire's brand data.

    This class is written to be resilient even if the underlying API
    or HTML changes: it uses safe dictionary access and falls back
    to minimal records when something goes wrong.
    """

    TOKEN_PATTERN = re.compile(r"(b_[A-Za-z0-9]+)")

    def __init__(self, session: requests.Session, base_url: str, timeout: float = 10.0):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def extract_token(cls, identifier: str) -> str:
        """
        Accept either a raw token (b_xxx) or a Faire URL containing the token.
        """
        identifier = identifier.strip()
        if identifier.startswith("b_"):
            return identifier

        match = cls.TOKEN_PATTERN.search(identifier)
        if match:
            return match.group(1)

        # As a last resort, normalize any remaining string.
        sanitized = re.sub(r"[^A-Za-z0-9_]", "", identifier)
        logger.debug("Could not detect token; using sanitized identifier '%s'", sanitized)
        return sanitized

    def fetch_brand(self, identifier: str) -> Dict[str, Any]:
        """
        Fetch brand details and return them as a structured dictionary.
        """
        token = self.extract_token(identifier)
        url = f"{self.base_url}/brands/{token}"

        logger.debug("Fetching brand data for token '%s' from %s", token, url)

        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            logger.warning("Network error while fetching brand %s: %s", token, e)
            info = BrandInfo(
                token=token,
                url=url,
                source_error=str(e),
            )
            return asdict(info)

        if not resp.ok:
            logger.warning(
                "Non-success status code %s while fetching brand %s",
                resp.status_code,
                token,
            )
            info = BrandInfo(
                token=token,
                url=url,
                source_error=f"HTTP {resp.status_code}",
            )
            return asdict(info)

        try:
            payload = resp.json()
        except ValueError:
            logger.warning("Response for brand %s is not JSON; returning minimal info", token)
            info = BrandInfo(
                token=token,
                url=url,
                source_error="Invalid JSON response",
            )
            return asdict(info)

        # Some APIs wrap brand under a key like "brand"
        brand_data = payload.get("brand", payload)

        info = BrandInfo(
            token=token,
            name=brand_data.get("name") or brand_data.get("brand_name"),
            description=brand_data.get("description"),
            short_description=brand_data.get("short_description"),
            url=brand_data.get("url") or url,
            instagram_handle=brand_data.get("instagram_handle")
            or (brand_data.get("social", {}) or {}).get("instagram"),
            country=brand_data.get("based_in") or brand_data.get("country"),
            made_in=brand_data.get("made_in"),
            active_products_count=self._safe_int(
                brand_data.get("active_products_count")
                or (brand_data.get("products_summary") or {}).get("active_count")
            ),
            lead_time_days=self._safe_int(
                brand_data.get("lead_time_days")
                or (brand_data.get("shipping") or {}).get("lead_time_days")
            ),
            first_order_minimum_amount=self._safe_float(
                (brand_data.get("first_order_minimum") or {}).get("amount")
                if isinstance(brand_data.get("first_order_minimum"), dict)
                else brand_data.get("first_order_minimum_amount")
            ),
            accepted_terms=brand_data.get("accepted_terms"),
            eco_friendly=brand_data.get("eco_friendly"),
            women_owned=brand_data.get("women_owned"),
            sold_on_amazon=brand_data.get("sold_on_amazon"),
            badges=brand_data.get("badges") or [],
            business_identifiers=brand_data.get("business_identifiers") or [],
            story_images=brand_data.get("story_images") or [],
            video_url=brand_data.get("video_url"),
            brand_reviews_summary=brand_data.get("brand_reviews_summary")
            or brand_data.get("reviews_summary"),
            vacation_start_date=parse_date_iso(
                (brand_data.get("vacation") or {}).get("start_date")
            ),
            vacation_end_date=parse_date_iso(
                (brand_data.get("vacation") or {}).get("end_date")
            ),
            vacation_banner_text=(brand_data.get("vacation") or {}).get("banner_text"),
            source_error=None,
        )

        return asdict(info)

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None