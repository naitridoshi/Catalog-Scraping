import asyncio
import gc
import json
import multiprocessing
import random
import re
import time
import csv
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Union

import httpx
import psutil
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup

from alShamali.constants import FIRST_PAGE_URL, HEADERS
from common.constants import BASIC_HEADERS
from common.custom_logger import color_string, get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("AlShamaliRequestHelper")
listener.start()


class AlShamaliRequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS, max_concurrent_requests: int = 5):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = []
        self.max_concurrent_requests = max_concurrent_requests
        logger.info(f"Initialized AlShamaliRequestHelper with max_concurrent_requests={max_concurrent_requests}")

    async def request(
            self,
            url: str,
            method: str = 'GET',
            timeout: int = 10,
            params: Optional[dict] = None,
            json: Optional[Union[dict, list]] = None,
            data: Optional[dict] = None,
            headers: Optional[dict] = None,
            client: Optional[httpx.AsyncClient] = None  # <- new
    ):
        logger.debug(f"Requesting {url} ...")

        headers = headers or self.headers
        proxies = self.proxies if self.proxies else None
        use_own_client = client is None

        if use_own_client:
            client = httpx.AsyncClient(timeout=timeout, proxy=proxies, verify=False)

        try:
            for try_request in range(1, 5):
                start_time = time.time()
                try:
                    logger.debug(f"Attempt {try_request}/4 for URL: {url}")
                    
                    # Add delay between retry attempts to avoid overwhelming the server
                    if try_request > 1:
                        delay = try_request * 2  # Progressive delay: 2s, 4s, 6s
                        logger.debug(f"Waiting {delay} seconds before retry {try_request}")
                        await asyncio.sleep(delay)
                    
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json,
                        data=data,
                        headers=headers,
                    )
                    time_taken = f'{time.time() - start_time:.2f} seconds'

                    if response.status_code == 200:
                        logger.debug(
                            f'Try: {try_request}, Status Code: {response.status_code}, '
                            f'Response Length: {len(response.text) / 1024 / 1024:.2f} MB, '
                            f'Time Taken: {color_string(time_taken)}.'
                        )
                        return response
                    else:
                        logger.warning(
                            f'REQUEST FAILED - {try_request}: Status Code: {response.status_code}, '
                            f'Text: {response.text[:300]}, Time Taken: {color_string(time_taken)}.'
                        )
                except Exception as err:
                    logger.error(
                        f'ERROR OCCURRED - {try_request}: Time Taken '
                        f"PAYLOAD - {json} "
                        f"{color_string(f'{time.time() - start_time:.2f} seconds')}, Error: {err}"
                    )
        finally:
            if use_own_client:
                await client.aclose()

        logger.error(f"All retry attempts failed for URL: {url}")
        return None

    async def get_last_page_url(self, soup):
        logger.debug(f"Getting last page url from soup...")
        pagination_div = soup.find('div', class_='tyresPaginator')
        if pagination_div:
            logger.debug("Found pagination div")
            pagination_class = pagination_div.find('ul', class_='fr-pagination')
            if pagination_class:
                logger.debug("Found pagination class")
                last_page_url = pagination_class.find('li', class_='last')
                if last_page_url:
                    logger.debug(f"Found last page url: {last_page_url}")
                    last_page_number = int(last_page_url.find('a').get('href').split('start=')[1])
                    logger.info(f"Found last page number: {last_page_number}")
                    return last_page_number
                else:   
                    logger.error("Not Found last page element in pagination")
                    return None
            else:
                logger.error("Not Found pagination class")
                return None
        else:
            logger.error("Not Found pagination div")
            return None

    async def get_all_pages_urls(self, url):
        logger.info(f"Getting all pages urls for {url} ...") 
        
        # First, get the initial page to determine pagination
        logger.debug("Fetching initial page to determine pagination...")
        initial_response = await self.request(url)
        if not initial_response:
            logger.error("Failed to fetch initial page")
            return []
            
        soup = BeautifulSoup(initial_response.text, 'html.parser')
        last_page_number = await self.get_last_page_url(soup)
        
        if last_page_number is None:
            logger.error("Could not determine last page number")
            return [url]
        
        all_pages_urls = []
        for page in range(0, last_page_number + 1, 20):
            page_url = f"{url}&start={page}"
            all_pages_urls.append(page_url)
        
        logger.info(f"Generated {len(all_pages_urls)} page URLs")
        return all_pages_urls

    async def parse_single_page(self, url: str, client: httpx.AsyncClient) -> list:
        """Parse a single page and return product data"""
        logger.debug(f"Parsing single page: {url}")
        
        try:
            # Add random delay before each request to avoid cookie-based blocking
            delay = random.uniform(1.5, 3.5)  # Random delay between 1.5-3.5 seconds
            logger.debug(f"Waiting {delay:.2f} seconds before requesting {url}")
            await asyncio.sleep(delay)
            
            response = await self.request(url, client=client)
            if not response:
                logger.error(f"Failed to get response for {url}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            main_products_div = soup.find('div', class_='goodsBody')

            if main_products_div:
                logger.debug(f"Found main products div for {url}")
            else:
                logger.warning(f"Not Found main products div for {url}, using original soup")
                main_products_div = soup
            
            products_table = main_products_div.find('div', class_='fr-table-responsive')
            if not products_table:
                logger.warning(f"No products table found for {url}")
                return []
                
            header_row = products_table.find('thead').find('tr')
            if not header_row:
                logger.warning(f"No header row found for {url}")
                return []
                
            header_row_columns = header_row.find_all('th')
            header_row_columns_text = [column.text.strip() for column in header_row_columns]
            logger.debug(f"Header columns for {url}: {header_row_columns_text}")
            
            products_rows = products_table.find('tbody').find_all('tr')
            logger.debug(f"Found {len(products_rows)} product rows for {url}")
            
            products_data = []
            for idx, product_row in enumerate(products_rows):
                product_row_columns = product_row.find_all('td')
                product_data = {}
                
                for i, column in enumerate(product_row_columns):
                    column_text = column.text.strip() if column.text.strip() else None
                    if i < len(header_row_columns_text):
                        product_data[header_row_columns_text[i]] = column_text
                    else:
                        logger.warning(f"Column index {i} out of range for headers in {url}")
                
                products_data.append(product_data)
                logger.debug(f"Processed product {idx + 1}/{len(products_rows)} for {url}")
            
            logger.info(f"Successfully parsed {len(products_data)} products from {url}")
            return products_data
            
        except Exception as e:
            logger.error(f"Error parsing page {url}: {str(e)}")
            return []

    async def parse_response(self):
        logger.info("Starting async parsing process...")
        start_time = time.time()
        
        # Get all page URLs
        all_pages_urls = await self.get_all_pages_urls(FIRST_PAGE_URL)
        logger.info(f"Total pages to process: {len(all_pages_urls)}")
        
        if not all_pages_urls:
            logger.error("No pages to process")
            return []

        # Create a shared client for better performance
        async with httpx.AsyncClient(timeout=30, proxy=self.proxies, verify=False) as client:
            # Process pages in batches for controlled concurrency
            all_products_data = []
            batch_size = self.max_concurrent_requests
            
            for i in range(0, len(all_pages_urls), batch_size):
                batch_urls = all_pages_urls[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_pages_urls) + batch_size - 1)//batch_size} "
                           f"({len(batch_urls)} pages)")
                
                # Create tasks for concurrent processing
                tasks = [self.parse_single_page(url, client) for url in batch_urls]
                
                # Execute batch concurrently
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"Exception in batch {i//batch_size + 1}, page {j + 1}: {result}")
                    else:
                        all_products_data.extend(result)
                        logger.debug(f"Added {len(result)} products from batch {i//batch_size + 1}, page {j + 1}")
                
                # Longer delay between batches to avoid cookie-based blocking
                if i + batch_size < len(all_pages_urls):
                    batch_delay = random.uniform(3, 6)  # Random delay between 3-6 seconds
                    logger.info(f"Completed batch {i//batch_size + 1}. Waiting {batch_delay:.2f} seconds before next batch...")
                    await asyncio.sleep(batch_delay)
        
        total_time = time.time() - start_time
        logger.info(f"Completed parsing {len(all_pages_urls)} pages in {total_time:.2f} seconds")
        logger.info(f"Total products collected: {len(all_products_data)}")
        
        return all_products_data


if __name__ == '__main__':
    logger.info("Starting AlShamali scraper...")
    scraper = AlShamaliRequestHelper(headers=HEADERS, max_concurrent_requests=5)
    
    try:
        result = asyncio.run(scraper.parse_response())
        
        # Save results
        with open('alShamali/NPR_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(result)} products to NPR_result.json")
        
        # Also save as CSV for easier analysis
        if result:
            csv_filename = 'alShamali/NPR_result.csv'
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                if result:
                    fieldnames = result[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(result)
            logger.info(f"Also saved results to {csv_filename}")
            
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise