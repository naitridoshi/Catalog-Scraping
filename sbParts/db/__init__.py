from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from common.config import MONGO_URI, DATABASE_NAME
from common.config.sbparts import SBPARTS_PARTS_COLLECTION
from common.custom_logger import get_logger

logger, listener = get_logger("SbpartsDB")
listener.start()

class MongoWriter:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def save_response(self, data):
        """
        Insert one or more documents with createdAt and updatedAt timestamps.
        Accepts either a dict (single document) or a list of dicts.
        """
        now = datetime.utcnow()

        try:
            if isinstance(data, list):
                if data:
                    for doc in data:
                        doc["createdAt"] = now
                        doc["updatedAt"] = now
                    await self.collection.insert_many(data)
                    logger.debug(f"Inserted {len(data)} documents with timestamps.")
                else:
                    logger.debug("Received empty list; nothing inserted.")
            elif isinstance(data, dict):
                data["createdAt"] = now
                data["updatedAt"] = now
                await self.collection.insert_one(data)
                logger.debug("Inserted 1 document with timestamps.")
            else:
                logger.warning(f"Unsupported data type for insertion: {type(data)}")
        except Exception as e:
            logger.error(f"Mongo insert failed: {e}")



mongo_writer=MongoWriter(mongo_uri=MONGO_URI, db_name=DATABASE_NAME, collection_name=SBPARTS_PARTS_COLLECTION)