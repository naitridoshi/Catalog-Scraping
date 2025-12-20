from pymongo import MongoClient

from common.config import MONGO_URI, DATABASE_NAME
from common.config.jinku import JINKU_MODELS_COLLECTION_NAME, JINKU_PRODUCTS_COLLECTION_NAME
from common.config.sbparts import SBPARTS_PARTS_COLLECTION

try:
    client = MongoClient(MONGO_URI)
    db= client[DATABASE_NAME]


    jinku_models_collection=db[JINKU_MODELS_COLLECTION_NAME]
    jinku_products_collection=db[JINKU_PRODUCTS_COLLECTION_NAME]
    #
    # jinku_products_collection.create_index([("createdAt", -1)])
    # jinku_products_collection.create_index([("jinku_product_id", 1)])
    # jinku_products_collection.create_index([("jinku_product_id", -1)])

except Exception as e:
    print(f"Error connecting to MongoDB: {str(e)}")
    jinku_models_collection = None
    jinku_products_collection = None

