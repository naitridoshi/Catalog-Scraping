from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    print(f".env file not found at path: {env_path}")

config = dotenv_values(env_path)
MONGO_URI=config.get("MONGO_URI")
DATABASE_NAME=config.get("DATABASE_NAME")

LOGGER_APP_NAME=config.get("LOGGER_APP_NAME")

