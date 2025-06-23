import asyncio
import gc
import json
import multiprocessing
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Union

import httpx
import psutil
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup

# from common.config import DATA_CENTER_PROXIES
from common.constants import BASIC_HEADERS, BATCH_SIZE, MAX_PROCESSES
from common.custom_logger import color_string, get_logger
from sbParts.constants import GET_PART_NUMBER_URL, CATALOG_PAGE_URL
from sbParts.db import mongo_writer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("SBpartsRequestHelper")
listener.start()

dubai_tz = pytz.timezone("Asia/Dubai")

class SbPartsRequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = multiprocessing.Manager().list()

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

    async def collect_all_part_numbers(self):
        logger.info("Starting collection of all part numbers.")
        no_response_prefixes = []  # List to store prefixes with no response
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []

            for i in range(10000):  # 0000 to 9999
                prefix = f"{i:04d}"
                payload = {"search_part": prefix}
                logger.debug(f"Creating task for prefix: {prefix}")

                async def fetch_and_store(prefix, payload):
                    logger.debug(f"Fetching data for prefix: {prefix}")
                    response = await self.request(
                        url=GET_PART_NUMBER_URL,
                        method="POST",
                        json=payload,
                        client=client
                    )
                    if response:
                        try:
                            data = response.json()
                            logger.debug(f"Received response for prefix {prefix}: {str(data)}")
                            logger.info(f"Valid data found for prefix {prefix}, saving to DB.")
                            await mongo_writer.save_response(data)
                            logger.info(f"Saved data for prefix {prefix}")
                        except ValueError as e:
                            logger.error(
                                f"Failed to parse JSON for prefix {prefix}: {e}. Raw response: {response.text}"
                            )
                        except Exception as e:
                            logger.error(f"Error processing response for {prefix}: {e}")
                    else:
                        logger.warning(f"No response received for prefix {prefix}.")
                        no_response_prefixes.append(prefix)  # Store prefix with no response

                tasks.append(fetch_and_store(prefix, payload))
                logger.debug(f"Task appended for prefix: {prefix}. Current batch size: {len(tasks)}")

                if len(tasks) == 50:
                    logger.info(f"Executing batch of 50 tasks. Last prefix in batch: {prefix}")
                    await asyncio.gather(*tasks)
                    logger.info(f"Batch of 50 tasks completed. Clearing task list.")
                    tasks = []

            if tasks:
                logger.info(f"Executing final batch of {len(tasks)} tasks.")
                await asyncio.gather(*tasks)
                logger.info("Final batch completed.")

        # Write no_response_prefixes to a file at the end
        import os
        os.makedirs('files', exist_ok=True)
        with open('files/no_response_prefixes.json', 'w') as f:
            json.dump(no_response_prefixes, f, indent=4)
        logger.info(f"Completed collection of all part numbers. No response for {len(no_response_prefixes)} prefixes. Saved to files/no_response_prefixes.json.")

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

    async def parse_catalog_page(self, part_no:str,pid: str, brand:str):
        logger.info(f"Starting to parse catalog page for PID: {pid}, Part No: {part_no}, Brand: {brand}")
        url = f"{CATALOG_PAGE_URL}{pid}"
        logger.debug(f"Constructed URL: {url}")
        
        response = await self.request(url)
        if response:
            logger.info(f"Received response for PID {pid}, status: {response.status_code}")
            logger.debug(f"Response content length: {len(response.text)} characters")
            
            soup = BeautifulSoup(response.text , 'html.parser')
            logger.debug("BeautifulSoup object created successfully")
            
            # Add null checks for all elements
            logger.debug("Looking for product header (h4 with class 'productHeader')")
            title_elem = soup.find('h4', class_='productHeader')
            if not title_elem:
                logger.error(f"Could not find product header for PID: {pid}")
                return []
            title = title_elem.get_text().strip().split('\n')[0].strip()
            logger.info(f"Found product title: '{title}'")
            
            logger.debug("Looking for product image (a tag with data-lightbox='product-image-set')")
            img_title=title.split('|')[-1]
            logger.info(f"Found product image title: {img_title}")
            img_elem = soup.find('a', attrs={'title':img_title.strip()})
            
            img_url = img_elem.get('href') if img_elem else None
            logger.info(f"Found product image URL: {img_url}")
            
            logger.debug("Looking for specifications div (div with class 'productspec')")
            specifications_div = soup.find('div', class_='productspec')
            specifications = {}
            if specifications_div:
                logger.debug("Found specifications div, looking for table")
                specifications_table = specifications_div.find('table',class_='table table-bordered table-striped marginbtnless')
                if specifications_table:
                    logger.debug("Found specifications table, processing rows")
                    specifications_rows = specifications_table.find_all('tr')
                    logger.info(f"Found {len(specifications_rows)} specification rows")
                    for count, row in enumerate(specifications_rows):
                            logger.debug(f"Processing specification row {count + 1}")
                            key_elem = row.find_all('td')[0]
                            value_elem = row.find_all('td')[-1]
                            if key_elem.get_text().strip() == 'Part Number':
                                continue
                            if key_elem and value_elem:
                                key = key_elem.get_text().strip()
                                value = value_elem.get_text().strip()
                                specifications[key] = value
                                logger.debug(f"Added specification: {key} = {value}")
                            else:
                                logger.warning(f"Row {count + 1}: Missing key or value element")
                    else:
                        logger.warning("tbody not found in specifications table")
                else:
                    logger.warning("Specifications table not found")
            else:
                logger.warning("Specifications div not found")
            
            logger.info(f"Collected {len(specifications)} specifications")
            
            logger.debug("Looking for cross-reference divs (div with class 'productapp')")
            cross_divs = soup.find_all('div', class_='productapp')
            logger.info(f"Found {len(cross_divs)} cross-reference divs")
            crosses = []
            for div_index, cross_div in enumerate(cross_divs):
                logger.debug(f"Processing cross-reference div {div_index + 1}")
                cross_table = cross_div.find('table')
                if cross_table:
                    logger.debug(f"Found table in cross-reference div {div_index + 1}")
                    cross_table_rows = cross_table.find_all('tr')
                    logger.debug(f"Found {len(cross_table_rows)} rows in cross-reference table {div_index + 1}")
                    for row_index, row in enumerate(cross_table_rows):
                        logger.debug(f"Processing cross-reference row {row_index + 1} in div {div_index + 1}")
                        tds = row.find_all('td')
                        if len(tds) >= 2:
                            key = tds[0].get_text().strip()
                            value = tds[-1].get_text().strip()
                            crosses.append({'Owner': key, 'Number': value})
                            logger.debug(f"Added cross-reference: {key} = {value}")
                        else:
                            logger.warning(f"Cross-reference row {row_index + 1} in div {div_index + 1}: Insufficient columns ({len(tds)})")
                else:
                    logger.warning(f"Cross-reference table not found in div {div_index + 1}")
            
            logger.info(f"Collected {len(crosses)} cross-references")
            
            all_docs = []
            logger.debug("Creating final documents")
            for cross_index, cross in enumerate(crosses):
                doc = {
                    'product_name': title,
                    'product_image': img_url,
                    'specifications': specifications,
                    'pid': pid,
                    'p_brand': brand,
                    'Owner': cross['Owner'],
                    'Number': cross['Number']
                }
                all_docs.append(doc)
                logger.debug(f"Created document {cross_index + 1}: Owner={cross['Owner']}, Number={cross['Number']}")

            logger.info(f"Successfully parsed catalog page for PID {pid}. Created {len(all_docs)} documents")
            return all_docs
        else:
            logger.error(f"No response received for PID: {pid}")
            return []

    async def read_from_file(self, filename: str):
        logger.info(f"Reading from file: {filename}")
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    async def main(self, filename: str):
        data = await self.read_from_file(filename)
        for count, item in enumerate(data):
            logger.info(f"Processing item {count + 1} of {len(data)}")
            all_docs=await self.parse_catalog_page(pid=item['pid'], part_no=item['part_no'], brand=item['p_brand'])
            logger.info(f"Processed item {count + 1} of {len(data)}")

            if all_docs:
                logger.info(f"Saving {len(all_docs)} documents for item {count + 1} of {len(data)}")
                await mongo_writer.save_response(all_docs)
                logger.info(f"Saved item {count + 1} of {len(data)}")
            else:
                logger.warning(f"No documents found for item {count + 1} of {len(data)}")
            break

if __name__ == '__main__':
    scraper = SbPartsRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    res=asyncio.run(scraper.parse_catalog_page(pid='241245', part_no='0046455892', brand='ALFA ROMEO'))
    print(json.dumps(res, indent=4))
