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
from sbParts.constants import GET_PART_NUMBER_URL
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
            client = httpx.AsyncClient(timeout=timeout, proxies=proxies, verify=False)

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
        logger.info("Completed collection of all part numbers.")

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


if __name__ == '__main__':
    scraper = SbPartsRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    _url = 'https://www.cp.pt/passageiros/en/how-to-travel/Useful-information'
    res = scraper.request('https://www.ifconfig.me/all.json')
    print(res.json())
    print(res.status_code)
