thonimport json
import logging
import os
import sys
from typing import List, Dict, Any

import requests

from extractors.brand_parser import BrandParser
from extractors.product_extractor import ProductExtractor
from outputs.json_exporter import JSONExporter

def load_settings() -> Dict[str, Any]:
    """
    Load configuration from config/settings.json relative to this file.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    settings_path = os.path.join(base_dir, "config", "settings.json")

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except FileNotFoundError:
        logging.error("settings.json not found at %s", settings_path)
        raise
    except json.JSONDecodeError as e:
        logging.error("Failed to parse settings.json: %s", e)
        raise

def load_brand_identifiers(project_root: str, input_path: str) -> List[str]:
    """
    Load brand URLs or tokens from the provided text file.
    """
    resolved_path = input_path
    if not os.path.isabs(resolved_path):
        resolved_path = os.path.join(project_root, input_path)

    if not os.path.exists(resolved_path):
        logging.warning("Input brands file not found at %s; using empty list", resolved_path)
        return []

    identifiers: List[str] = []
    with open(resolved_path, "r", encoding="utf-8") as f:
        for line in f:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            identifiers.append(value)

    logging.info("Loaded %d brand identifiers from %s", len(identifiers), resolved_path)
    return identifiers

def main(argv: List[str]) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    logger = logging.getLogger("faire-brand-scraper")

    try:
        settings = load_settings()
    except Exception:
        logger.error("Could not load configuration; exiting.")
        return 1

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Determine input and output paths
    input_file = settings.get("input_file", "data/input_brands.txt")
    output_file = settings.get("output_file", "data/sample_output.json")

    # CLI overrides: main.py [input_file] [output_file]
    if len(argv) >= 2:
        input_file = argv[1]
    if len(argv) >= 3:
        output_file = argv[2]

    identifiers = load_brand_identifiers(project_root, input_file)
    if not identifiers:
        logger.warning("No brand identifiers provided; nothing to scrape.")
        return 0

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": settings.get(
                "user_agent",
                "FaireBrandScraper/1.0 (+https://bitbash.dev)",
            )
        }
    )

    base_url = settings.get("faire_base_url", "https://www.faire.com/api")
    timeout = float(settings.get("timeout_seconds", 10))

    brand_parser = BrandParser(session=session, base_url=base_url, timeout=timeout)
    product_extractor = ProductExtractor(
        session=session, base_url=base_url, timeout=timeout
    )
    exporter = JSONExporter()

    results: List[Dict[str, Any]] = []

    logger.info("Starting scrape for %d brands", len(identifiers))

    for idx, raw_identifier in enumerate(identifiers, start=1):
        logger.info("Processing %d/%d: %s", idx, len(identifiers), raw_identifier)
        try:
            brand_data = brand_parser.fetch_brand(raw_identifier)
            product_data = product_extractor.fetch_product_stats(raw_identifier)

            # Merge data dictionaries, product data overwriting on key collision
            merged = {**brand_data, **product_data}
            results.append(merged)
        except Exception as e:
            logger.exception("Unexpected error while processing %s: %s", raw_identifier, e)

    # Resolve output path
    if not os.path.isabs(output_file):
        output_path = os.path.join(project_root, output_file)
    else:
        output_path = output_file

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    exporter.save(results, output_path)
    logger.info("Scrape finished; %d records saved to %s", len(results), output_path)

    return 0

if __name__ == "__main__":
    try:
        exit_code = main(sys.argv)
    except KeyboardInterrupt:
        logging.getLogger("faire-brand-scraper").warning("Interrupted by user.")
        exit_code = 1
    sys.exit(exit_code)