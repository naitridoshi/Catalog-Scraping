import json
import os
from pathlib import Path
from pymongo import MongoClient
from common.custom_logger import get_logger

logger, listener = get_logger("SuzukiDataProcessor")
listener.start()

def process_suzuki_files():
    """
    Read JSON files from files/suzuki directory, add car_model key to each dictionary,
    and store them in a MongoDB collection named 'suzuki'.
    """
    try:
        # Connect to MongoDB
        MONGO_URI=""
        DATABASE_NAME=""

        client = MongoClient(MONGO_URI)
        db = client[DATABASE_NAME]
        suzuki_collection = db['suzuki_catalog_data']
        
        # Path to the suzuki files directory
        suzuki_files_path = Path("files/suzuki")
        
        if not suzuki_files_path.exists():
            logger.error(f"Directory {suzuki_files_path} does not exist")
            return
        
        # Get all JSON files in the directory
        json_files = list(suzuki_files_path.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No JSON files found in {suzuki_files_path}")
            return
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        total_documents = 0
        
        for json_file in json_files:
            try:
                # Extract car model from filename (remove .json extension and clean up)
                car_model = json_file.stem
                
                logger.info(f"Processing file: {json_file.name} with car model: {car_model}")
                
                # Read JSON file
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, list):
                    logger.warning(f"File {json_file.name} does not contain a list of dictionaries")
                    continue
                
                # Add car_model key to each dictionary
                documents_to_insert = []
                for item in data:
                    if isinstance(item, dict):
                        # Create a copy to avoid modifying the original data
                        document = item.copy()
                        document['car_model'] = car_model
                        documents_to_insert.append(document)
                    else:
                        logger.warning(f"Skipping non-dictionary item in {json_file.name}")
                
                if documents_to_insert:
                    # Insert documents into MongoDB
                    result = suzuki_collection.insert_many(documents_to_insert)
                    logger.info(f"Inserted {len(result.inserted_ids)} documents from {json_file.name}")
                    total_documents += len(result.inserted_ids)
                else:
                    logger.warning(f"No valid documents found in {json_file.name}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON file {json_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error processing file {json_file.name}: {e}")
        
        logger.info(f"Total documents inserted: {total_documents}")
        
        # Create indexes for better query performance
        suzuki_collection.create_index([("car_model", 1)])
        suzuki_collection.create_index([("PartNum", 1)])
        suzuki_collection.create_index([("PartName", 1)])
        
        logger.info("Successfully created indexes on car_model, PartNum, and PartName fields")
        
    except Exception as e:
        logger.error(f"Error connecting to MongoDB or processing files: {e}")
    finally:
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed")

if __name__ == "__main__":
    process_suzuki_files()
