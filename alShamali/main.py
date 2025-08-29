import asyncio
import json
import os
import random
import pandas as pd
from datetime import datetime
from alShamali.request_helper import AlShamaliRequestHelper
from alShamali.constants import HEADERS
from common.custom_logger import get_logger    

logger, listener = get_logger("AlShamaliScraper")
listener.start()

async def process_item(item, scraper, save:bool=True):
    """Process a single item asynchronously"""
    try:
        # Add delay before processing each item to avoid cookie-based blocking
        item_delay = random.uniform(2, 5)  # Random delay between 2-5 seconds
        logger.debug(f"Waiting {item_delay:.2f} seconds before processing {item['title']}...")
        await asyncio.sleep(item_delay)
        
        logger.info(f"Processing item: {item['title']}")
        data = await scraper.parse_response(item['link'], item['title'], item['image'])

        if data:
            csv_path = None
            csv_content = None
            if save:
                # Save to JSON
                json_filename = f"{item['title'].replace(' ', '_').replace('/', '_')}_data"
                scraper.save_to_json(data, json_filename)

                # Save to CSV
                csv_filename = f"{item['title'].replace(' ', '_').replace('/', '_')}_data"
                csv_path = scraper.save_to_csv(data, csv_filename, item['title'])
            else:
                # Get CSV content as a string for in-memory operations
                csv_content = scraper.get_csv_content_as_string(data, item['title'])

            logger.info(f"Successfully processed {item['title']}: {len(data)} items")
            return {
                'title': item['title'],
                'data': data,
                'csv_path': csv_path,
                'csv_content': csv_content,
                'count': len(data)
            }
        else:
            logger.warning(f"No data found for {item['title']}")
            return {
                'title': item['title'],
                'data': [],
                'csv_path': None,
                'csv_content': None,
                'count': 0
            }
    except Exception as e:
        logger.error(f"Error processing {item['title']}: {str(e)}")
        return {
            'title': item['title'],
            'data': [],
            'csv_path': None,
            'csv_content': None,
            'count': 0,
            'error': str(e)
        }



def create_excel_workbook(results, output_filename="alShamali_combined_data.xlsx"):
    """Create a single Excel workbook with all CSV data as separate sheets"""
    try:
        # Create files directory if it doesn't exist
        os.makedirs('files/alShamali', exist_ok=True)
        excel_path = f'files/alShamali/{output_filename}'
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Add summary sheet
            summary_data = []
            for result in results:
                summary_data.append({
                    'Category': result['title'],
                    'Total Items': result['count'],
                    'Status': 'Success' if result['csv_path'] else 'Failed',
                    'Error': result.get('error', '')
                })
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add individual sheets for each category
            for result in results:
                if result['data']:
                    # Clean sheet name (Excel has limitations on sheet names)
                    sheet_name = result['title'][:31].replace('/', '_').replace('\\', '_').replace('*', '_').replace('[', '_').replace(']', '_').replace(':', '_').replace('?', '_')
                    
                    # Convert data to DataFrame
                    df = pd.DataFrame(result['data'])
                    
                    # Process price data if Price column exists
                    if 'Price' in df.columns:
                        # Parse price data using scraper's method
                        price_data = df['Price'].apply(scraper.parse_price_data)
                        
                        # Create separate columns for AED and USD
                        df['Price_AED'] = price_data.apply(lambda x: x['AED'])
                        df['Price_USD'] = price_data.apply(lambda x: x['USD'])
                        
                        # Keep original price column for reference
                        df['Price_Original'] = df['Price']
                        
                        # Remove the original Price column to avoid confusion
                        df = df.drop('Price', axis=1)
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    logger.info(f"Added sheet '{sheet_name}' with {len(df)} rows")
        
        logger.info(f"Successfully created Excel workbook: {excel_path}")
        return excel_path
        
    except Exception as e:
        logger.error(f"Error creating Excel workbook: {str(e)}")
        return None

async def main():
    logger.info("Starting AlShamali scraper...")
    
    # Add initial delay to avoid immediate cookie-based blocking
    # initial_delay = random.uniform(1, 5)  # Random delay between 5-10 seconds
    # logger.info(f"Initial delay: Waiting {initial_delay:.2f} seconds before starting...")
    # await asyncio.sleep(initial_delay)
    
    logger.info("Loading items...")
    
    with open('alShamali/items.json', 'r') as f:
        items = json.load(f)

    logger.info(f"Loaded {len(items)} items")

    # Create a single scraper instance
    scraper = AlShamaliRequestHelper(headers=HEADERS, max_concurrent_requests=5)
    
    # Process items concurrently with controlled concurrency
    max_concurrent = 3  # Limit concurrent processing to avoid overwhelming the server
    results = []
    
    for i in range(0, len(items), max_concurrent):
        batch = items[i:i + max_concurrent]
        logger.info(f"Processing batch {i//max_concurrent + 1}/{(len(items) + max_concurrent - 1)//max_concurrent} "
                   f"({len(batch)} items)")
        
        # Process batch concurrently
        tasks = [process_item(item, scraper) for item in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Exception in batch {i//max_concurrent + 1}, item {j + 1}: {result}")
                results.append({
                    'title': batch[j]['title'],
                    'data': [],
                    'csv_path': None,
                    'count': 0,
                    'error': str(result)
                })
            else:
                results.append(result)
        
        # Add delay between batches to avoid cookie-based blocking
        if i + max_concurrent < len(items):
            batch_delay = random.uniform(8, 15)  # Random delay between 8-15 seconds
            logger.info(f"Waiting {batch_delay:.2f} seconds before next batch...")
            await asyncio.sleep(batch_delay)
    
    # Create combined Excel workbook
    logger.info("Creating combined Excel workbook...")
    excel_path = create_excel_workbook(results)
    
    # Print summary
    total_items = sum(result['count'] for result in results)
    successful_categories = sum(1 for result in results if result['csv_path'])
    
    logger.info(f"Scraping completed!")
    logger.info(f"Total categories processed: {len(results)}")
    logger.info(f"Successful categories: {successful_categories}")
    logger.info(f"Total items scraped: {total_items}")
    
    if excel_path:
        logger.info(f"Combined Excel workbook saved to: {excel_path}")

async def run_alshamali_scraper_and_return_df(selected_items: list[dict], output_option: str):
    logger.info(f"Starting AlShamali scraper for Streamlit app with output option: {output_option}")

    initial_delay = random.uniform(1, 3)
    logger.info(f"Initial delay: Waiting {initial_delay:.2f} seconds before starting...")
    await asyncio.sleep(initial_delay)

    if not selected_items:
        logger.warning("No items selected to scrape.")
        return None, None

    scraper = AlShamaliRequestHelper(headers=HEADERS, max_concurrent_requests=5)

    max_concurrent = 3
    results = []

    for i in range(0, len(selected_items), max_concurrent):
        batch = selected_items[i:i + max_concurrent]
        logger.info(f"Processing batch {i//max_concurrent + 1}/{(len(selected_items) + max_concurrent - 1)//max_concurrent} "
                   f"({len(batch)} items)")
        # When called from streamlit, always use save=False
        tasks = [process_item(item, scraper, save=False) for item in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Exception in batch {i//max_concurrent + 1}, item {j + 1}: {result}")
                results.append({
                    'title': batch[j]['title'],
                    'data': [],
                    'count': 0,
                    'error': str(result)
                })
            else:
                results.append(result)

        if i + max_concurrent < len(selected_items):
            batch_delay = random.uniform(3, 5)
            logger.info(f"Waiting {batch_delay:.2f} seconds before next batch...")
            await asyncio.sleep(batch_delay)

    if output_option == 'Combine into a single data table':
        all_data = []
        for result in results:
            if result.get('data'):
                all_data.extend(result['data'])

        if all_data:
            df = pd.DataFrame(all_data)
            if 'Price' in df.columns:
                price_data = df['Price'].apply(scraper.parse_price_data)
                df['Price_AED'] = price_data.apply(lambda x: x['AED'])
                df['Price_USD'] = price_data.apply(lambda x: x['USD'])
                df['Price_Original'] = df['Price']
                df = df.drop('Price', axis=1)
            return df, None
        else:
            return pd.DataFrame(), None
    else: # Separate files
        processed_results = []
        for result in results:
            brand_df = pd.DataFrame(result['data']) if result.get('data') else pd.DataFrame()
            if not brand_df.empty and 'Price' in brand_df.columns:
                price_data = brand_df['Price'].apply(scraper.parse_price_data)
                brand_df['Price_AED'] = price_data.apply(lambda x: x['AED'])
                brand_df['Price_USD'] = price_data.apply(lambda x: x['USD'])
                brand_df['Price_Original'] = brand_df['Price']
                brand_df = brand_df.drop('Price', axis=1)
            
            processed_results.append({
                'title': result.get('title', 'N/A'),
                'count': result.get('count', 0),
                'status': 'Success' if result.get('count', 0) > 0 else 'Failed',
                'error': result.get('error', ''),
                'dataframe': brand_df,
                'csv_content': result.get('csv_content', '')
            })
        return None, processed_results

def get_all_brands():
    alshamali_items_path = "alShamali/items.json"
    alshamali_brands = []
    if os.path.exists(alshamali_items_path):
        with open(alshamali_items_path, 'r') as f:
            alshamali_items_data = json.load(f)
    return alshamali_items_data


if __name__ == "__main__":
    asyncio.run(main())