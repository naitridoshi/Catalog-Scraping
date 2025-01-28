from pymongo import MongoClient

from config import MONGO_URI, DATABASE_NAME, JINKU_MODELS_COLLECTION_NAME

client = MongoClient(MONGO_URI)
db= client[DATABASE_NAME]

jinku_models_collection=db[JINKU_MODELS_COLLECTION_NAME]