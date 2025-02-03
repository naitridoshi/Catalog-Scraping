from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    raise Exception(".env file not found")

config = dotenv_values(env_path)
MONGO_URI=config.get("MONGO_URI")
DATABASE_NAME=config.get("DATABASE_NAME")
JINKU_MODELS_COLLECTION_NAME=config.get("JINKU_MODELS_COLLECTION_NAME")
JINKU_MAX_RETRIES=int(config.get("JINKU_MAX_RETRIES"))