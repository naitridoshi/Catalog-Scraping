import json

import curl
import requests

from config import JINKU_MAX_RETRIES
from constants import JINKU_BRANDS, JINKU_PAYLOAD, JINKU_CATALOG_URL, JINKU_HEADERS
from db import jinku_models_collection
from logger import logger


class JinkuCrawler:

    def __init__(self):
        self.cookie = ""
        self.xsrf_token = ""

    @staticmethod
    def send_request(url, headers, payload, params=None):
        response = requests.post(url, headers=headers, data=payload, params=params)
        return response

    @staticmethod
    def parse_response_to_get_models_list(data):
        logger.info("Parsing Response to get Models")
        models_dict = data.get("serverMemo").get("data").get("models")
        if models_dict is None:
            logger.error(f"Some Error in parsing response to get models - Data - {data}")
            raise Exception("parse_response_to_get_models_list Error")
        for model in models_dict:
            models_dict[model]["jinku_model_id"] = model
            jinku_models_collection.insert_one(models_dict[model])

    @staticmethod
    def set_payload(payload_to_set):
        JINKU_PAYLOAD["updates"][0]["payload"]["params"].clear()
        JINKU_PAYLOAD["updates"][0]["payload"]["params"].extend(payload_to_set)
        return json.dumps(JINKU_PAYLOAD)

    def set_cookies(self):
        logger.debug("Setting New Cookies")
        payload = self.set_payload(["profileType", None])

        if JINKU_HEADERS.get("cookie"):
            JINKU_HEADERS.pop("cookie")
        if JINKU_HEADERS.get("x-csrf-token"):
            JINKU_HEADERS.pop("x-csrf-token")

        response = self.send_request(url=JINKU_CATALOG_URL, headers=JINKU_HEADERS, payload=payload)
        self.cookie = ""
        self.xsrf_token = ""

        for header in response.headers:
            if header == "Set-Cookie":
                self.cookie += response.headers.get("Set-Cookie")
        self.xsrf_token = response.cookies.get("XSRF-TOKEN")

        self.set_headers()

    def set_headers(self):
        JINKU_HEADERS.update({'cookie': self.cookie,
                              'x-csrf-token': self.xsrf_token, })

    def get_model_lists(self):
        self.set_cookies()
        logger.info("Getting model lists")
        for brand in JINKU_BRANDS:
            logger.info(f"Crawling Model Lists for Brand - {brand} - {JINKU_BRANDS.get(brand)}")
            payload = self.set_payload(["brand", str(brand)])
            for retry in range(JINKU_MAX_RETRIES):
                response = self.send_request(JINKU_CATALOG_URL, JINKU_HEADERS, payload)

                if response.status_code == 419:
                    if retry == JINKU_MAX_RETRIES - 1:
                        logger.critical(
                            f"Max Retries done -  Received 419 Status Code - Brand - {brand} - Data Received - {response.text}")
                        raise Exception("Max Retries Complete for getting model lists")

                    logger.error(
                        f"Try Request - {retry} - Received 419 Status Code - Brand - {brand} - Data Received - {response.text}")
                    self.set_cookies()

                if response.status_code == 200:
                    logger.info(f"Received 200 Status Code - Data Received - {response.json()}")
                    data = response.json()
                    self.parse_response_to_get_models_list(data)
                    logger.info(f"Complete Crawling Models of Brand - {brand}")
                    break

                else:
                    if retry == JINKU_MAX_RETRIES - 1:
                        logger.critical(
                            f"Max Retries done - Received Status Code - {response.status_code} - Brand - {brand} - Data Received - {response.text}")
                        raise Exception("Max Retries Complete for getting model lists")

                    logger.error(f"Received Status Code - {response.status_code} - response data - {response.text}")
                    self.set_cookies()

        logger.info("Completed Crawling Model lists for all Brands")


if __name__ == '__main__':
    jinku_crawler = JinkuCrawler()
    jinku_crawler.set_cookies()
    jinku_crawler.get_model_lists()
    logger.info("DONE")
