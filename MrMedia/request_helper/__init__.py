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
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone
from typing import Optional, Union, List, Dict

import httpx
import psutil
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
from httpx import Response

from MrMedia.constants import MRMEDIA_HEADERS, CATEGORY_URL
from common.constants import BASIC_HEADERS
from common.custom_logger import color_string, get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("MrMediaRequestHelper")
listener.start()


class MrMediaRequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS, max_concurrent_requests: int = 5):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = []
        self.max_concurrent_requests = max_concurrent_requests
        logger.info(f"Initialized MrMediaRequestHelper with max_concurrent_requests={max_concurrent_requests}")

    @staticmethod
    def get_list_of_urls(response:Response):
        soup = BeautifulSoup(response.text, 'html.parser')
        categories_class = soup.find("div", class_="containe")

        if categories_class:
            category_links=categories_class.find_all('a')
        else:
            category_links = soup.find_all('a')

        return category_links

    def parse_category_page(self, response:Response):
        soup=BeautifulSoup(response.text, 'html.parser')
        all_items=soup.find('div', class_='container py-5').find('div', class_='row').find_all('div', class_='col-lg-4')
        for item in all_items:
            item_data = {}
            details=item.find("div", class_="work__item").find_all("li", class_="list-group-item float-left")
            for count,detail in enumerate(details):
                if count == 0:
                    item_data['Title'] = detail.text.strip()
                else:
                    if ":" in detail.text:
                        detail_text = detail.text.strip().split(":", 1)
                        if len(detail_text) == 2:
                            key = detail_text[0].strip()
                            value = detail_text[1].strip()
                            item_data[key] = value
                        else:
                            item_data[f'Detail_{str(uuid)[:3]}'] = detail_text[0].strip()

            logger.debug(f"Parsed item data: {item_data}")

            self.shared_list.append(item_data)

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
                        delay = try_request * 3  # Increased progressive delay: 3s, 6s, 9s
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
                        f"{color_string(f'{time.time() - start_time:.2f} seconds')}, Error: {err}"
                        f"PAYLOAD - {json} "
                    )
        finally:
            if use_own_client:
                await client.aclose()

        logger.error(f"All retry attempts failed for URL: {url}")
        return None

    def save_to_csv(self, data: list, filename: str):
        if not data:
            logger.warning(f"No data to save for {filename}")
            return
        os.makedirs("files/mrMedia", exist_ok=True)
        csv_path = f"files/mrMedia/{filename}.csv"
        keys = set().union(*(d.keys() for d in data))
        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(keys))
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"Data saved to {csv_path}")

    def save_to_json(self, data: list, filename: str):
        if not data:
            logger.warning(f"No data to save for {filename}")
            return
        os.makedirs("files/mrMedia/json", exist_ok=True)
        json_path = f"files/mrMedia/json/{filename}.json"
        with open(json_path, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, ensure_ascii=False, indent=2)
        logger.info(f"Backup JSON saved to {json_path}")

    def get_csv_content_as_string(self, data: list):
        if not data:
            return ""
        
        import io
        keys = set().union(*(d.keys() for d in data))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(keys))
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    async def main(self, url):
        import asyncio
        from functools import partial

        response = await self.request(
            url=url,
            method='GET',
            timeout=10,
            headers=self.headers,
            client=httpx.AsyncClient()
        )
        if not response:
            logger.error(f"Failed to get a valid response for URL: {url}")
            return None

        all_categories = self.get_list_of_urls(response)
        if not all_categories:
            logger.warning(f"No categories found in response for URL: {url}")
            return None
        else:
            logger.info(f"Found {len(all_categories)} categories in response for URL: {url}")

        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def process_category(category):
            category_url = category.get('href')
            if not category_url:
                logger.warning(f"Category link is empty for URL: {url}")
                return

            if not category_url.startswith('http'):
                category_url = f"{url.rstrip('/allcategories.php/')}/{category_url.lstrip('/')}"

            logger.info(f"Processing category URL: {category_url}")
            async with semaphore:
                category_response = await self.request(
                    url=category_url,
                    method='GET',
                    timeout=10,
                    headers=self.headers,
                    client=httpx.AsyncClient()
                )
            if not category_response:
                logger.error(f"Failed to get a valid response for category URL: {category_url}")
                return

            # Parse and save in a thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            def parse_and_save():
                    self.parse_category_page(category_response)
                    os.makedirs("files/mrMedia", exist_ok=True)
                    csv_path = f"files/mrMedia/category_{category.text}.csv"
                    self.save_to_csv(self.shared_list, filename=f"category_{category.text}")
                    self.save_to_json(self.shared_list, filename=f"category_{category.text}")
                    logger.info(f"Saved category data to {csv_path} and backup to files/mrMedia/json/category_{category.text}.json")

            await loop.run_in_executor(None, parse_and_save)

        tasks = [process_category(category) for category in all_categories]
        await asyncio.gather(*tasks)

    async def get_all_category_links(self):
        response = await self.request(url=CATEGORY_URL, method='GET', headers=self.headers)
        if response:
            links_with_headers = []
            logger.info(f"Response received for URL: {CATEGORY_URL}")
            links = self.get_list_of_urls(response)
            logger.info(f"Total Links found: {len(links)}")
            for link in links:
                links_with_headers.append({"name": link.text, "link": link.get('href')})
            return links_with_headers
        return []

    async def get_category_page(self, category_url: str) -> list:
        """Parses a single category page and returns a list of item dicts."""
        self.shared_list = []  # Clear previous data
        
        # Construct full URL if needed
        if not category_url.startswith('http'):
            base_url = CATEGORY_URL.split('/allcategories.php')[0]
            category_url = f"{base_url}/{category_url.lstrip('/')}"

        response = await self.request(url=category_url, method='GET', headers=self.headers)
        if response:
            logger.info(f"Response received for URL: {category_url}")
            self.parse_category_page(response)
            logger.info(f"Successfully parsed {len(self.shared_list)} items from {category_url}")
            return self.shared_list
        else:
            logger.error(f"Failed to get response for {category_url}")
            return []



if __name__ == '__main__':


    asyncio.run(MrMediaRequestHelper(headers=MRMEDIA_HEADERS).main("https://directory.mymrmedia.com/allcategories.php"))
    # asyncio.run(test_category())
    # asyncio.run(test())