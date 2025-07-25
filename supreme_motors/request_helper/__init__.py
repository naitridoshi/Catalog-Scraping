import asyncio
import gc
import json
import multiprocessing
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

from common.constants import BASIC_HEADERS
from common.custom_logger import color_string, get_logger
from supreme_motors.constants import MAIN_PRODUCTS_URL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("SupremeMotorsRequestHelper")
listener.start()



class SupremeMotorsRequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = []

    @staticmethod
    def httpx_request_to_curl(request: httpx.Request) -> str:
        curl_cmd = [
            "curl",
            "-X", request.method,
        ]

        # Add headers
        for k, v in request.headers.items():
            curl_cmd.extend(["-H", f'"{k}: {v}"'])

        # Add data (for POST/PUT)
        if request.content:
            curl_cmd.extend(["--data-raw", f"'{request.content.decode()}'"])

        # Add URL
        curl_cmd.append(f'"{str(request.url)}"')

        return " ".join(curl_cmd)

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

        return None

    async def get_list_of_urls(self, url: str):
        response = await self.request(url)
        if response is None:
            logger.error("No response")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        product_category=soup.find('div', class_="cate_row_con")
        if product_category:
            logger.info("Found product category....")
            urls = set([a['href'] for a in product_category.find_all('a', href=True) if
                        ("suprememotorparts" in str(a['href']) and str(a['href']).startswith("http")) or str(a['href']).startswith(
                            "/")])
        else:
            logger.warning("No product category found....")
            urls = set([a['href'] for a in soup.find_all('a', href=True) if
                        ("suprememotorparts" in str(a['href']) and str(a['href']).startswith("http")) or str(
                            a['href']).startswith(
                            "/")])

        logger.debug(f'Extracted {len(urls)} URLs')
        return urls

    async def parse_url(self, url):
        logger.info(f"Starting to parse URL: {url}")
        response = await self.request(url)
        if response is None:
            logger.error("No response")
            return None

        logger.debug("Creating BeautifulSoup object from response text")
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.debug("Looking for product-info-section div")
        product_section_soup = soup.find('div', class_="product-info-section clearfix")
        if not product_section_soup:
            logger.warning("Product info section not found, using entire soup")
            product_section_soup = soup

        logger.debug("Looking for main image area div")
        image_div = product_section_soup.find('div', class_="main-image-area slick-slide slick-current slick-active")
        if not image_div:
            logger.warning("Image Div not found!!")
            logger.debug("Looking for any img tag in product section")
            image_tag = product_section_soup.find('img')
            if image_tag and image_tag.has_attr('src'):
                image_url = image_tag['src']
                logger.debug(f"Image URL: {image_url}")
            else:
                image_url = None
                logger.warning("Image Tag not found!!")
        else:
            logger.debug("Found main image area div, looking for img tag within it")
            image_tag = image_div.find('img')
            if image_tag and image_tag.has_attr('src'):
                image_url = image_tag['src']
                logger.debug(f"Image URL: {image_url}")
            else:
                image_url = None
                logger.warning("Image Tag not found!!")

        logger.debug("Looking for product heading div")
        product_name_div = product_section_soup.find('div', class_="product-heading")
        if product_name_div:
            product_name = product_name_div.getText(strip=True)
            logger.debug(f"Product Name Found - {product_name}")
        else:
            product_name = None
            logger.warning(f"Product Name Not Found!!")

        logger.debug("Looking for other info section")
        other_info_section = soup.find('div', class_="other-info-section")
        if other_info_section:
            logger.debug("Found other info section, extracting product details")
            all_details = []
            detail_section = other_info_section.find_all('ul', class_="clearfix")
            logger.debug(f"Found {len(detail_section)} detail sections")
            for section in detail_section:
                product_details = {}
                all_points = section.find_all('li')
                logger.debug(f"Processing {len(all_points)} points in detail section")
                for point in all_points:
                    label = point.find('label').getText(strip=True)
                    value = point.find('span').getText(strip=True)
                    product_details[label] = [value]
                all_details.append(product_details)
        else:
            logger.warning("Other info section not found")
            all_details = []

        logger.debug("Looking for product description section")
        product_description_div = other_info_section.find('div', class_="product-description-section") if other_info_section else None
        if product_description_div:
            product_description = product_description_div.getText(strip=False)
            logger.debug("Product description found")
        else:
            product_description = None
            logger.warning("Product description not found")

        logger.info(f"Parsing completed for URL: {url}")
        logger.debug(f"Extracted data - Name: {product_name}, Image URL: {image_url}, Details count: {len(all_details)}")
        
        return {
            "Name": product_name,
            "Link": url,
            "Image Url": image_url,
            "Product Details": all_details,
            "Product Description": product_description
        }

    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = []
        self.csv_filename = None
        self.csv_writer = None
        self.csv_file = None
        self.all_columns = [
            'Name', 'Link', 'Image Url', 'Product Description',
            # Pricing and Order Information
            'Minimum Order Quantity', 'Price', 'FOB Port', 'Payment Terms',
            # Product Specifications
            'Parts Name', 'Application', 'Product Type', 'Size',
            # Business Information
            'Supply Ability', 'Delivery Time', 'Sample Available', 'Sample Policy',
            'Packaging Details', 'Main Export Market(s)', 'Main Domestic Market', 'Certifications'
        ]

    def initialize_csv(self):
        """Initialize the CSV file and write header"""
        try:
            # Create directory if it doesn't exist
            os.makedirs('../../files/supreme_motors', exist_ok=True)
            
            # Create CSV filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.csv_filename = f"../../files/supreme_motors/supreme_motors_products_{timestamp}.csv"
            
            # Open CSV file and create writer
            self.csv_file = open(self.csv_filename, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Write header
            self.csv_writer.writerow(self.all_columns)
            
            logger.info(f"CSV file initialized: {self.csv_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing CSV file: {e}")
            return False

    def add_row_to_csv(self, data: dict):
        """Add a single row to the CSV file"""
        try:
            if not self.csv_writer:
                logger.error("CSV file not initialized")
                return False
            
            # Prepare row data
            row_data = {}
            
            # Add basic fields
            row_data['Name'] = data.get('Name', '')
            row_data['Link'] = data.get('Link', '')
            row_data['Image Url'] = data.get('Image Url', '')
            row_data['Product Description'] = data.get('Product Description', '').replace('\n', ' ').strip()
            
            # Process product details
            product_details = data.get('Product Details', [])
            for detail_dict in product_details:
                for key, values in detail_dict.items():
                    if isinstance(values, list):
                        # Join multiple values with semicolon
                        row_data[key] = '; '.join(values)
                    else:
                        row_data[key] = str(values)
            
            # Write row with all columns (empty string for missing values)
            row = []
            for column in self.all_columns:
                row.append(row_data.get(column, ''))
            
            self.csv_writer.writerow(row)
            return True
            
        except Exception as e:
            logger.error(f"Error adding row to CSV: {e}")
            return False

    def close_csv(self):
        """Close the CSV file"""
        try:
            if self.csv_file:
                self.csv_file.close()
                logger.info(f"CSV file closed: {self.csv_filename}")
                return self.csv_filename
        except Exception as e:
            logger.error(f"Error closing CSV file: {e}")
        return None

    async def parse_url_with_csv(self, url: str):
        """Parse URL and add to CSV"""
        data = await self.parse_url(url)
        if data:
            success = self.add_row_to_csv(data)
            return data, success
        return None, None

    @staticmethod
    def clean_text_from_json(filename: str):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            for item in data:
                item['data'] = re.sub(r'\s+', ' ', item['data'].strip())
            with open('data2.json', 'w') as f:
                json.dump(data, f, indent=4)
            logger.debug('Cleaned text saved to data2.json')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error processing file {filename}: {e}")

    async def main(self):
        # Initialize CSV file
        if not self.initialize_csv():
            logger.error("Failed to initialize CSV file")
            return
        
        try:
            # Get all URLs first
            all_urls = await self.get_list_of_urls(MAIN_PRODUCTS_URL)
            if not all_urls:
                logger.error("No URLs found")
                return
            
            logger.info(f"Found {len(all_urls)} URLs to process")
            
            # Limit concurrent operations to 10
            semaphore = asyncio.Semaphore(10)
            
            async def parse_url_with_limit(url: str):
                async with semaphore:
                    return await self.parse_url_with_csv(url)
            
            # Process URLs in parallel using asyncio with limited concurrency
            tasks = []
            for url in all_urls:
                task = asyncio.create_task(parse_url_with_limit(url))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing URL {list(all_urls)[i]}: {result}")
                elif result[0] is not None:  # data is not None
                    successful_results.append(result[0])
                    self.shared_list.append(result[0])
                    logger.info(f"Successfully processed URL {list(all_urls)[i]}")
            
            # Save all data to JSON file
            with open('data2.json', 'w') as f:
                json.dump(self.shared_list, f, indent=4)
            
            logger.info(f"Processing completed. {len(successful_results)} URLs processed successfully.")
            
        finally:
            # Close CSV file
            csv_file = self.close_csv()
            if csv_file:
                logger.info(f"All data saved to CSV: {csv_file}")


if __name__ == '__main__':
    scraper = SupremeMotorsRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    
    # Test parse_url method and CSV creation
    async def test_parse_url_and_csv():
        # Test with a sample URL from the main products page
        test_url = "https://www.suprememotorparts.com/automotive-piston-ring-set-10016405.html"
        print(f"Testing parse_url with: {test_url}")
        
        result = await scraper.parse_url(test_url)
        if result:
            print("✅ parse_url test successful!")
            print("Retrieved data:")
            print(json.dumps(result, indent=2))
            
            # Test CSV creation
            print("\n" + "="*50)
            print("Testing CSV creation...")
            
            # Initialize CSV
            if scraper.initialize_csv():
                print("✅ CSV file initialized")
                
                # Add row to CSV
                if scraper.add_row_to_csv(result):
                    print("✅ Row added to CSV successfully")
                    
                    # Close CSV and read content
                    csv_file = scraper.close_csv()
                    if csv_file:
                        print(f"✅ CSV file created successfully: {csv_file}")
                        print("CSV file structure:")
                        try:
                            with open(csv_file, 'r', encoding='utf-8') as f:
                                csv_content = f.read()
                                print(csv_content)
                        except Exception as e:
                            print(f"❌ Error reading CSV file: {e}")
                    else:
                        print("❌ Error closing CSV file")
                else:
                    print("❌ Error adding row to CSV")
            else:
                print("❌ CSV file initialization failed")
        else:
            print("❌ parse_url test failed - no data retrieved")
    
    # Run the test
    asyncio.run(test_parse_url_and_csv())
