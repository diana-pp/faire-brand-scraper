thonfrom datetime import datetime
from typing import Optional

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in a few common formats and return a datetime.

    If parsing fails or the input is falsy, returns None instead of raising.
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()
    # Try ISO format first
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Last resort: let fromisoformat try, if available
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None

def parse_date_iso(date_str: Optional[str]) -> Optional[str]:
    """
    Parse a string to a datetime, then return an ISO 8601 date string (YYYY-MM-DD).

    Returns None if parsing fails.
    """
    if not date_str:
        return None
    dt = parse_date(date_str)
    if not dt:
        return None
    return dt.date().isoformat()