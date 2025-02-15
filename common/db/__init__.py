from pymongo import MongoClient

from common.config import MONGO_URI, DATABASE_NAME
from common.config.jinku import JINKU_MODELS_COLLECTION_NAME, JINKU_PRODUCTS_COLLECTION

client = MongoClient(MONGO_URI)
db= client[DATABASE_NAME]

jinku_models_collection=db[JINKU_MODELS_COLLECTION_NAME]
jinku_products_collection=db[JINKU_PRODUCTS_COLLECTION]