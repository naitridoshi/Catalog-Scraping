from os import path

from dotenv import dotenv_values

env_path = ".env"

if not path.exists(env_path):
    raise Exception(".env file not found")

config = dotenv_values(env_path)

SBPARTS_PARTS_COLLECTION=config.get("SBPARTS_PARTS_COLLECTION")