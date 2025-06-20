import gc
import json
import multiprocessing
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone

import psutil
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup

from common.constants import BASIC_HEADERS, BATCH_SIZE, MAX_PROCESSES
from common.custom_logger import color_string, get_logger
from common.db import jinku_products_collection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("SuzukiRequestHelper")
listener.start()


class SuzukiRequestHelper:
    BASIC_HEADERS.update({'content-type': 'application/json'})
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers

    def request(self, url: str, method: str = 'GET', timeout: int = 10,params:dict=None,json:dict | list =None, data:str |None = None,headers:dict=None):
        logger.debug(f"Requesting {url} ...")
        for try_request in range(1, 5):
            start_time = time.time()
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    data=data,
                    headers=self.headers if headers is None else headers,
                    proxies=self.proxies,
                    verify=False,
                    timeout=timeout,
                    stream=True
                )
                time_taken = f'{time.time() - start_time:.2f} seconds'
                if response.status_code == 200:
                    logger.debug(
                        f'Try: {try_request}, '
                        f'Status Code: {response.status_code}, '
                        f'Response Length: '
                        f'{len(response.text) / 1024 / 1024:.2f} MB, '
                        f'Time Taken: {color_string(time_taken)}.'
                    )
                    return response
                else:
                    logger.warning(
                        f'REQUEST FAILED - {try_request}: '
                        f'Status Code: {response.status_code}, '
                        f'Time Taken: {color_string(time_taken)}.'
                    )
            except Exception as err:
                logger.error(
                    f'ERROR OCCURRED - {try_request}: Time Taken '
                    f"{color_string(f'{time.time() - start_time:.2f} seconds')}"
                    f', Error: {err}'
                )


    def get_filters_data(self, model_id:str, model_name:str, page:int = 1):
        logger.info(f"Getting filters data for {model_name} {model_id} {page}")
        payload= {
          "category": [],
          "model": [
            {
              "modelname": model_name,
              "modelid": model_id,
              "variant": [
                {}
              ]
            }
          ],
          "sortingFilter": "By Relevence",
          "pageNumber": page,
          "query": ""
        }

        response=self.request(url="https://www.marutisuzuki.com/api/sitecore/MSGPAJAX/GetFilter", method="POST", json=payload)
        if response:
            return response.text


if __name__ == '__main__':

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://www.marutisuzuki.com",
        "priority": "u=1, i",
        "referer": "https://www.marutisuzuki.com/genuine-parts?utm_source=google&utm_medium=cpc&utm_campaign=MSGP_Brand_Search_Generic&utm_id=%7Bcampaignid%7D&utm_term=%7Bkeyword%7D&utm_content=search&utm_source=google&utm_medium=cpc&utm_campaign=22079570581&utm_term=maruti%20suzuki%20parts&utm_content=c&gad_source=1",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        "cookie": "marutisuzuki#lang=en"
    }

    scraper = RequestHelper(
        headers=headers
    )

    res = scraper.get_filters_data(model_id="P", model_name="a-star", page=1)
    print("RESPONSE",res)
