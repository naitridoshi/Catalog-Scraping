import asyncio
import json
import random
from alShamali.request_helper import AlShamaliRequestHelper
from alShamali.constants import HEADERS
from common.custom_logger import get_logger

logger, listener = get_logger("AlShamaliTest")
listener.start()

async def test_async_scraping():
    """Test the asynchronous scraping with a small subset of items"""
    
    # Load items
    with open('alShamali/items.json', 'r') as f:
        all_items = json.load(f)
    
    # Take only first 2 items for testing
    test_items = all_items[:2]
    logger.info(f"Testing with {len(test_items)} items")
    
    # Create scraper
    scraper = AlShamaliRequestHelper(headers=HEADERS, max_concurrent_requests=3)
    
    # Process items
    results = []
    for item in test_items:
        # Add delay between items to avoid cookie-based blocking
        if len(results) > 0:  # Skip delay for first item
            item_delay = random.uniform(3, 7)  # Random delay between 3-7 seconds
            logger.info(f"Waiting {item_delay:.2f} seconds before next item...")
            await asyncio.sleep(item_delay)
            
        logger.info(f"Testing item: {item['title']}")
        try:
            data = await scraper.parse_response(item['link'], item['title'], item['image'])
            
            if data:
                # Save to JSON
                json_filename = f"test_{item['title'].replace(' ', '_').replace('/', '_')}_data"
                scraper.save_to_json(data, json_filename)
                
                # Save to CSV
                csv_filename = f"test_{item['title'].replace(' ', '_').replace('/', '_')}_data"
                csv_path = scraper.save_to_csv(data, csv_filename, item['title'])
                
                results.append({
                    'title': item['title'],
                    'count': len(data),
                    'csv_path': csv_path
                })
                
                logger.info(f"✓ Successfully processed {item['title']}: {len(data)} items")
            else:
                logger.warning(f"✗ No data found for {item['title']}")
                results.append({
                    'title': item['title'],
                    'count': 0,
                    'csv_path': None
                })
                
        except Exception as e:
            logger.error(f"✗ Error processing {item['title']}: {str(e)}")
            results.append({
                'title': item['title'],
                'count': 0,
                'csv_path': None,
                'error': str(e)
            })
    
    # Print summary
    total_items = sum(result['count'] for result in results)
    successful = sum(1 for result in results if result['count'] > 0)
    
    logger.info(f"\n=== TEST RESULTS ===")
    logger.info(f"Total items tested: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Total products scraped: {total_items}")
    
    for result in results:
        status = "✓" if result['count'] > 0 else "✗"
        logger.info(f"{status} {result['title']}: {result['count']} items")

if __name__ == "__main__":
    asyncio.run(test_async_scraping()) 