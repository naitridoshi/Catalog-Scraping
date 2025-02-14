from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    raise Exception(".env file not found")

config = dotenv_values(env_path)
MONGO_URI=config.get("MONGO_URI")
DATABASE_NAME=config.get("DATABASE_NAME")

LOGGER_APP_NAME=config.get("LOGGER_APP_NAME")

