
import json
from pathlib import Path
from typing import List

from pymongo import MongoClient

MONGO_URI = "mongodb://mongo:DTpMpOfsDGAoFSUCjkEmbfGlwhaKqvhm@caboose.proxy.rlwy.net:33343/"
DB_NAME = "amip-trading-backend"
COLLECTION_NAME = "catalog_data_copy"

OUTPUT_FILE_PATH = (
    "unique_jinku_product_ids.json"
)


def _validate_config() -> None:
    """Ensure DB config placeholders are populated before running the script."""
    missing_fields = [
        name
        for name, value in (
            ("MONGO_URI", MONGO_URI),
            ("DB_NAME", DB_NAME),
            ("COLLECTION_NAME", COLLECTION_NAME),
        )
        if not value
    ]
    if missing_fields:
        raise ValueError(
            f"Missing configuration values: {', '.join(missing_fields)}. "
            "Please fill in the placeholders before running the script."
        )


def get_unique_jinku_product_ids_from_db() -> List[dict]:
    """Fetch and persist all unique `jinku_product_id`+`jinku_url` pairs."""
    _validate_config()

    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]

    pipeline = [
        {"$match": {"jinku_product_id": {"$nin": [None, ""]}}},
        {
            "$group": {
                "_id": "$jinku_product_id",
                "jinku_url": {"$first": "$jinku_url"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    aggregated_docs = list(collection.aggregate(pipeline))
    unique_products = [
        {"jinku_product_id": doc["_id"], "jinku_url": doc.get("jinku_url")}
        for doc in aggregated_docs
    ]

    OUTPUT_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE_PATH.open("w", encoding="utf-8") as fp:
        json.dump(
            {"count": len(unique_products), "products": unique_products},
            fp,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Stored {len(unique_products)} products at {OUTPUT_FILE_PATH}")
    return unique_products


if __name__ == "__main__":
    get_unique_jinku_product_ids_from_db()
