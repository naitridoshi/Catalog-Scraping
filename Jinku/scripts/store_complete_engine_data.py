#!/usr/bin/env python3
"""
Populate model and engine details for every Jinku product stored in MongoDB.

The script expects complete_engine_related_data.json and updates each Mongo
document that shares a jinku_product_id with the JSON entries. Every document
receives:
  * model_and_engine_details – structured blocks grouped by brand/manufacturer
  * brand_search_tokens     – lower-cased brand/manufacturer names
  * model_search_tokens     – lower-cased model codes (mods)
  * engine_search_tokens    – lower-cased engine codes
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from common.custom_logger import get_logger

# Mongo connection placeholders – update these or provide environment variables.
MONGO_URI = os.environ.get(
    "JINKU_MONGO_URI", "mongodb://mongo:DTpMpOfsDGAoFSUCjkEmbfGlwhaKqvhm@caboose.proxy.rlwy.net:33343/"
)
MONGO_DB_NAME = os.environ.get("JINKU_MONGO_DB", "amip-trading-backend")
MONGO_COLLECTION_NAME = os.environ.get("JINKU_MONGO_COLLECTION", "catalog_data_copy")

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_FILE = ROOT_DIR / "complete_engine_related_data.json"
BULK_BATCH_SIZE = 500

logging, listener = get_logger("Engine Data Script")
listener.start()


def _validate_connection_details() -> None:
    """Guard against accidentally running the script with placeholder values."""

    placeholders = {
        "<username>",
        "<password>",
        "<host>",
        "<port>",
        "<auth_db>",
        "<database_name>",
        "<collection_name>",
    }
    target_strings = {
        MONGO_URI or "",
        MONGO_DB_NAME or "",
        MONGO_COLLECTION_NAME or "",
    }

    if any(token in value for value in target_strings for token in placeholders):
        raise RuntimeError(
            "Mongo connection details still contain placeholders. "
            "Edit store_complete_engine_data.py or provide the "
            "JINKU_MONGO_* environment variables before running the script."
        )


def _load_json_records(data_file: Path) -> Sequence[dict]:
    """Return the list of product entries from the JSON export."""

    if not data_file.exists():
        raise FileNotFoundError(f"Could not find data file at {data_file}")

    with data_file.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        results = payload.get("results", [])
    elif isinstance(payload, list):
        results = payload
    else:
        raise ValueError("Unexpected JSON structure in engine data file.")

    logging.info("Loaded %s records from %s", len(results), data_file)
    return results


def _clean_strings(values: Iterable[str]) -> List[str]:
    """Return a list of unique, non-empty strings while preserving order."""

    cleaned: List[str] = []
    seen = set()

    for value in values or []:  # type: ignore[arg-type]
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)

    return cleaned


@dataclass
class ModelEngineDetail:
    brand: str | None
    manufacturer: str | None
    mods: List[str]
    engine_codes: List[str]
    engine_capacities: List[str]

    def to_document(self) -> dict:
        """Serialize the dataclass to the format stored in Mongo."""

        return {
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "mods": self.mods,
            "engine_codes": self.engine_codes,
            "engine_capacities": self.engine_capacities,
        }


def _normalize_detail_block(detail: dict) -> ModelEngineDetail | None:
    """Normalize one item from model_and_engine_details."""

    if not isinstance(detail, dict):
        return None

    brand = (detail.get("brand") or "").strip() or None
    manufacturer = (detail.get("class") or "").strip() or None

    mods = _clean_strings(detail.get("mod") or [])
    engine_codes = _clean_strings(detail.get("eng_code") or [])
    engine_capacities = _clean_strings(detail.get("eng_cc") or [])

    if not any([brand, manufacturer, mods, engine_codes, engine_capacities]):
        return None

    return ModelEngineDetail(
        brand=brand,
        manufacturer=manufacturer,
        mods=mods,
        engine_codes=engine_codes,
        engine_capacities=engine_capacities,
    )


def _normalize_details(raw_details: Sequence[dict]) -> List[dict]:
    """Convert raw detail entries into the structure stored in Mongo."""

    normalized = []
    for detail in raw_details or []:  # type: ignore[arg-type]
        processed = _normalize_detail_block(detail)
        if processed:
            normalized.append(processed.to_document())

    return normalized


def _extend_tokens(target: List[str], seen: set[str], values: Iterable[str | None]) -> None:
    """Append normalized tokens to target if they have not been seen yet."""

    for value in values:
        if value is None:
            continue
        token = str(value).strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        target.append(token)


def _build_token_sets(details: Sequence[dict]) -> Dict[str, List[str]]:
    """Return separate token buckets for brand, model, and engine searches."""

    brand_tokens: List[str] = []
    model_tokens: List[str] = []
    engine_tokens: List[str] = []

    brand_seen: set[str] = set()
    model_seen: set[str] = set()
    engine_seen: set[str] = set()

    for detail in details:
        _extend_tokens(
            brand_tokens,
            brand_seen,
            [detail.get("brand"), detail.get("manufacturer")],
        )
        _extend_tokens(model_tokens, model_seen, detail.get("mods", []))
        _extend_tokens(engine_tokens, engine_seen, detail.get("engine_codes", []))

    return {
        "brand_search_tokens": brand_tokens,
        "model_search_tokens": model_tokens,
        "engine_search_tokens": engine_tokens,
    }


def _chunked(iterable: Iterable[UpdateOne], size: int) -> Iterable[List[UpdateOne]]:
    """Yield UpdateOne operations in fixed-size batches."""

    batch: List[UpdateOne] = []
    for op in iterable:
        batch.append(op)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _build_update_operations(records: Sequence[dict]) -> Iterable[UpdateOne]:
    """Create the UpdateOne operations for every scraped record."""

    for record in records:
        product_id = (record or {}).get("jinku_product_id")
        if not product_id:
            continue

        normalized_details = _normalize_details(record.get("model_and_engine_details", []))
        token_sets = _build_token_sets(normalized_details)
        current_time = datetime.now(timezone.utc)

        yield UpdateOne(
            {"jinku_product_id": product_id},
            {
                "$set": {
                    "model_and_engine_details": normalized_details,
                    **token_sets,
                    "updatedAt": current_time,
                }
            },
            upsert=False,
        )


def _apply_updates(collection: Collection, operations: Iterable[UpdateOne]) -> tuple[int, int]:
    """Execute the updates in batches and return matched/modified counts."""

    total_matched = 0
    total_modified = 0

    for batch in _chunked(operations, BULK_BATCH_SIZE):
        result = collection.bulk_write(batch, ordered=False)
        total_matched += result.matched_count
        total_modified += result.modified_count
        logging.info(
            "Batch updated %s documents (matched=%s, modified=%s)",
            len(batch),
            result.matched_count,
            result.modified_count,
        )

    return total_matched, total_modified


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Store normalized model/engine details for each Jinku product."
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="Path to complete_engine_related_data.json (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and parse records without touching MongoDB.",
    )
    return parser.parse_args()


def main() -> None:

    args = parse_args()

    records = _load_json_records(args.data_file)
    operations = list(_build_update_operations(records))
    logging.info("Prepared %s update operations", len(operations))

    if args.dry_run:
        logging.info("Dry run enabled – skipping MongoDB updates.")
        return

    _validate_connection_details()
    client = MongoClient(MONGO_URI)
    collection = client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]

    try:
        matched, modified = _apply_updates(collection, operations)
        logging.info("Completed updates (matched=%s, modified=%s).", matched, modified)
    except PyMongoError as exc:
        logging.exception("Mongo bulk write failed: %s", exc)
        raise SystemExit(1) from exc
    finally:
        client.close()


if __name__ == "__main__":
    main()
