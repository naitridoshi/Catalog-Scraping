from common.custom_logger import get_logger
from suzuki.constants import MODELS, SUZUKI_HEADERS
from suzuki.request_helper import SuzukiRequestHelper
import json
import pandas as pd
import asyncio
import csv
import io

logger, listener = get_logger("SuzukiMain")
listener.start()

def get_all_models():
    try:
        return MODELS
    except Exception as e:
        logger.error(f"An error occurred while fetching models - {str(e)}")
        return {}

def get_csv_content_as_string(data: list):
    if not data:
        return ""
    
    keys = set().union(*(d.keys() for d in data))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(keys))
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()

import asyncio
from concurrent.futures import ThreadPoolExecutor

async def scrape_single_model(model_info: dict):
    model_name = model_info.get("model_name")
    model_id = model_info.get("model_id")
    logger.info(f"Processing model: {model_name}")
    scraper = SuzukiRequestHelper(headers=SUZUKI_HEADERS)
    part_list_for_model = []

    try:
        # 1. Initial request for page 0 to get total pages
        logger.info(f"ID: {model_id} NAME: {model_name} PAGE: 0 (getting total pages)")
        initial_res = scraper.get_filters_data(model_id=model_id, model_name=model_name, page=0)
        
        if not initial_res:
            logger.warning(f"No initial response for {model_name}. Skipping.")
            return {'title': model_name, 'data': [], 'count': 0}

        total_pages = initial_res.get("TotalPages")
        part_list_for_model.extend(initial_res.get("PartList", []))

        if total_pages is None or total_pages <= 1:
            logger.info(f"Only one page found for {model_name}.")
        else:
            logger.info(f"Found {total_pages} pages for {model_name}. Fetching concurrently.")
            
            # 2. Concurrent requests for remaining pages
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=10) as executor:
                tasks = []
                for page_num in range(1, total_pages):
                    task = loop.run_in_executor(
                        executor, 
                        scraper.get_filters_data, 
                        model_id, 
                        model_name, 
                        page_num
                    )
                    tasks.append(task)
                
                # 3. Aggregate results
                responses = await asyncio.gather(*tasks)
                for res in responses:
                    if res and res.get("PartList"):
                        part_list_for_model.extend(res.get("PartList"))

    except Exception as e:
        logger.error(f"An error occurred while processing pages for {model_name}: {e}")

    for part in part_list_for_model:
        part['Model Name'] = model_name
    logger.info(f"Completed model: {model_name} with {len(part_list_for_model)} parts.")
    return {
        'title': model_name,
        'data': part_list_for_model,
        'count': len(part_list_for_model)
    }

async def run_suzuki_scraper_and_return_df(selected_models: list, output_option: str):
    logger.info("Starting Suzuki scraper for Streamlit app...")
    
    tasks = [scrape_single_model(model) for model in selected_models]
    results = await asyncio.gather(*tasks)

    if output_option == 'Combine into a single data table':
        all_data = []
        for result in results:
            if result.get('data'):
                all_data.extend(result['data'])
        if all_data:
            return pd.DataFrame(all_data), None
        else:
            return pd.DataFrame(), None
    else: # Separate files
        processed_results = []
        for result in results:
            model_df = pd.DataFrame(result['data']) if result.get('data') else pd.DataFrame()
            csv_content = get_csv_content_as_string(result['data'])
            
            processed_results.append({
                'title': result.get('title', 'N/A'),
                'count': result.get('count', 0),
                'status': 'Success' if result.get('count', 0) > 0 else 'Failed',
                'dataframe': model_df,
                'csv_content': csv_content
            })
        return None, processed_results


if __name__ == '__main__':
    # This block is for standalone execution and will save files to disk.
    async def main():
        for model_name, model_id in MODELS.items():
            result = await scrape_single_model({"model_name": model_name, "model_id": model_id})
            part_list = result['data']
            
            if part_list:
                file_model_name = model_name.replace(" ", "_").replace("(", "_").replace(")", "_").replace("-", "_").replace(".", "_").replace("'", "_").replace('"', "_").replace("/", "_").lower()
                
                import os
                output_dir = "files/suzuki"
                os.makedirs(output_dir, exist_ok=True)
                
                with open(f"{output_dir}/{file_model_name}.json", "w") as f:
                    json.dump(part_list, f, indent=4)
                logger.info(f"Saved {len(part_list)} parts for {model_name} to {file_model_name}.json")

    asyncio.run(main())