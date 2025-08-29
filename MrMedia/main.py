import asyncio
import json

import pandas as pd
from MrMedia.request_helper import MrMediaRequestHelper
from common.custom_logger import get_logger

logger, listener = get_logger("MrMediaScraper")
listener.start()


async def get_all_categories():
    try:
        categories_filename = "MrMedia/mr_media_categories.json"
        with open(categories_filename, "r") as f:
            categories = json.load(f)
        logger.info(f"Loaded {len(categories)} categories from {categories_filename}")
        return categories
    except Exception as e:
        logger.error(f"An error occurred while fetching categories - {str(e)}")
        return []


def run_mr_media_scraper_and_return_df(selected_categories: list, output_option: str):
    try:
        logger.info(f"Starting Mr Media scraper for Streamlit app with {len(selected_categories)} categories.")
        request_helper = MrMediaRequestHelper()

        async def scrape_categories():
            tasks = [request_helper.get_category_page(category.get("link")) for category in selected_categories]
            results_data = await asyncio.gather(*tasks)
            
            # Pair results back with their original category info
            results = []
            for i, data in enumerate(results_data):
                results.append({
                    'title': selected_categories[i].get('name'),
                    'data': data
                })

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
                    category_df = pd.DataFrame(result['data']) if result.get('data') else pd.DataFrame()
                    csv_content = request_helper.get_csv_content_as_string(result['data'])
                    
                    processed_results.append({
                        'title': result.get('title', 'N/A'),
                        'count': len(category_df),
                        'status': 'Success' if not category_df.empty else 'Failed',
                        'dataframe': category_df,
                        'csv_content': csv_content
                    })
                return None, processed_results

        # Run the async function and get the results
        combined_df, brand_results = asyncio.run(scrape_categories())
        
        logger.info(f"Successfully completed scraping for Mr. Media.")
        return combined_df, brand_results

    except Exception as e:
        logger.error(f"An error occurred in run_mr_media_scraper_and_return_df - {str(e)}")
        return pd.DataFrame(), None


if __name__ == '__main__':
    all_categories = asyncio.run(get_all_categories())
    with open("mr_media_categories.json", "w") as f:
        json.dump(all_categories, f, indent=4)
    logger.info(f"Saved {len(all_categories)} categories to mr_media_categories.json")