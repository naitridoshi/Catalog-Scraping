from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    print(f".env file not found at path: {env_path}")

config = dotenv_values(env_path)

SBPARTS_PARTS_COLLECTION=config.get("SBPARTS_PARTS_COLLECTION")
SBPARTS_CATALOG_COLLECTION=config.get("SBPARTS_CATALOG_COLLECTION", )