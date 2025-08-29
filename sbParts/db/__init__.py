from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from common.config import MONGO_URI, DATABASE_NAME
from common.config.sbparts import SBPARTS_CATALOG_COLLECTION
from common.custom_logger import get_logger

logger, listener = get_logger("SbpartsDB")
listener.start()

class MongoWriter:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def clean_mongo_data(self, data):
        """
        Clean MongoDB extended JSON format from data.
        Removes _id fields with $oid values and other MongoDB-specific fields.
        """
        if isinstance(data, dict):
            # Remove _id field if it exists (MongoDB will generate a new one)
            if '_id' in data:
                del data['_id']
            
            # Clean nested dictionaries
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = self.clean_mongo_data(value)
                elif isinstance(value, list):
                    data[key] = [self.clean_mongo_data(item) if isinstance(item, dict) else item for item in value]
        
        return data

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
                        doc = self.clean_mongo_data(doc)
                        doc["createdAt"] = now
                        doc["updatedAt"] = now
                    await self.collection.insert_many(data)
                    logger.debug(f"Inserted {len(data)} documents with timestamps.")
                else:
                    logger.debug("Received empty list; nothing inserted.")
            elif isinstance(data, dict):
                data = self.clean_mongo_data(data)
                data["createdAt"] = now
                data["updatedAt"] = now
                await self.collection.insert_one(data)
                logger.debug("Inserted 1 document with timestamps.")
            else:
                logger.warning(f"Unsupported data type for insertion: {type(data)}")
        except Exception as e:
            logger.error(f"Mongo insert failed: {e}")


try:
    mongo_writer=MongoWriter(mongo_uri=MONGO_URI, db_name=DATABASE_NAME, collection_name=SBPARTS_CATALOG_COLLECTION)
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {str(e)}")
    mongo_writer=None