thonimport json
import logging
from typing import Any, Iterable, List, Dict

logger = logging.getLogger(__name__)

class JSONExporter:
    """
    Export scraped records to a JSON file.
    """

    def save(self, records: Iterable[Dict[str, Any]], path: str) -> None:
        """
        Persist the records to disk as a JSON array.
        """
        # Materialize iterable in case it's a generator
        data: List[Dict[str, Any]] = list(records)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Failed to write JSON output to %s: %s", path, e)
            raise