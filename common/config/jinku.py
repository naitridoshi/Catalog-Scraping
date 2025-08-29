from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    print(f".env file not found at path: {env_path}")

config = dotenv_values(env_path)

JINKU_MODELS_COLLECTION_NAME=config.get("JINKU_MODELS_COLLECTION_NAME")
JINKU_MAX_RETRIES=int(config.get("JINKU_MAX_RETRIES",3))
JINKU_CSRF_TOKEN=config.get("JINKU_CSRF_TOKEN")
JINKU_COOKIE=config.get("JINKU_COOKIE")

JINKU_PRODUCTS_COLLECTION_NAME=config.get("JINKU_PRODUCTS_COLLECTION_NAME")
