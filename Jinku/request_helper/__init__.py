import gc
import json
import multiprocessing
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import psutil
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
import pandas as pd

# from common.config import DATA_CENTER_PROXIES
from common.constants import BASIC_HEADERS, BATCH_SIZE, MAX_PROCESSES
from common.custom_logger import color_string, get_logger
from common.db import jinku_products_collection
from common.request_helper import RequestHelper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("JinkuRequestHelper")
listener.start()

dubai_tz = pytz.timezone("Asia/Dubai")

class JinkuRequestHelper(RequestHelper):
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        super().__init__(proxies, headers)
        self.shared_list = multiprocessing.Manager().list() # Still needed for DB worker if used
        self.collected_data = []


    def get_list_of_urls(self, url: str):
        response = self.request(url)
        if response is None:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        search_result_class=soup.find(class_="searchresult")
        if search_result_class:
            logger.debug("Found Search Result Class....")
            urls = list(set([a['href'] for a in search_result_class.find_all('a', href=True)
                             if 'https://www.jikiu.com/catalogue/' in str(a['href'])]))
        else:
            urls = list(set([a['href'] for a in soup.find_all('a', href=True)
                             if 'https://www.jikiu.com/catalogue/' in str(a['href'])]))

        logger.debug(f'Extracted {len(urls)} URLs')
        return urls

    def insert_to_db_worker(self):
        """Database worker to insert data in batches from the shared list."""
        while True:
            if len(self.shared_list) >= BATCH_SIZE:
                batch = list(self.shared_list[:BATCH_SIZE])
                del self.shared_list[:BATCH_SIZE]  # Remove inserted items
                try:
                    jinku_products_collection.insert_many(batch)
                    logger.info(f"Inserted batch of {len(batch)} products.")
                except Exception as e:
                    logger.error(f"Batch insertion failed: {e}")
            time.sleep(1)  # Sleep briefly to avoid busy waiting

    @staticmethod
    def check_memory():
        """Check system memory to avoid excessive consumption."""
        mem = psutil.virtual_memory()
        memory_available=mem.available / mem.total
        logger.warning(f"Memory Available - {memory_available}")
        return memory_available > 0.2  # Ensure at least 20% free memory

    @staticmethod
    def format_product_details_for_df(url: str, product_details: str, product_images: list,
                                      specifications_dict: dict, crosses_list: list, return_df:bool=False) -> list[dict]:
        if product_details:
            product_name = product_details.split("|")[0].strip()
            jinku_product_id = product_details.split("|")[-1].split("-")[-1].strip()
        else:
            logger.error("Product Details is None")
            product_name = None
            jinku_product_id = None

        if return_df:
            base_doc = {
                "jikiu_url": url,
                "product_name": product_name,
                "product_image": product_images,
                "jikiu_product_id": jinku_product_id,
                "specifications": specifications_dict
            }
        else:
            base_doc = {
                "jinku_url": url,
                "product_name": product_name,
                "product_image": product_images,
                "jinku_product_id": jinku_product_id,
                "specifications": specifications_dict
            }

        formatted_data = []
        if not crosses_list:
            formatted_data.append(base_doc)
        else:
            for cross in crosses_list:
                cross_doc = base_doc.copy()
                if isinstance(cross, dict):
                    cross_doc.update(cross)
                else:
                    cross_doc.update({"Owner": cross, "Number": None}) # Assuming cross is just a string here
                formatted_data.append(cross_doc)
        return formatted_data

    def format_and_store_product_details_in_database(self,url:str, product_details:str, product_images:list,
                                                     specifications_dict:dict, crosses_list:list):

        if product_details:
            product_name=product_details.split("|")[0].strip()
            jinku_product_id=product_details.split("|")[-1].split("-")[-1].strip()
        else:
            logger.error("Product Details is None")
            product_name=None
            jinku_product_id=None

        base_doc= {
            "jinku_url": url,
            "product_name":product_name,
            "product_image":product_images,
            "jinku_product_id":jinku_product_id,
            "specifications":specifications_dict
        }

        for cross in crosses_list:
            cross_doc = base_doc.copy()
            if isinstance(cross, dict):
                cross_doc.update(cross)
            else:
                cross_doc.update({cross: None})
            cross_doc["createdAt"] = datetime.now(dubai_tz)
            cross_doc["updatedAt"] = datetime.now(dubai_tz)
            self.shared_list.append(cross_doc)

        logger.debug(f"Appended {len(crosses_list)} documents in Shared List .... ")

    def parse_jinku_data_from_soup(self,soup:BeautifulSoup, url:str):
        logger.debug("Parsing Jinku Data from the soup")

        if soup is None:
            logger.critical("Soup is None")
            raise Exception("Empty Soup")

        name_class = soup.find(class_="d-lg-flex justify-content-between")
        product_details = name_class.find('h2').text.strip() if name_class else None
        product_images=[]
        images = soup.find_all('img')
        for img in images:
            if img.get('src'):
                product_images.append(img.get('src'))

        if len(product_images)==0:
             logger.warning("Product Image Not found")

        logger.info(f"Product details found - {product_details}")

        specification_region = soup.find(class_="detail__plate row")

        if not specification_region:
            logger.error("Specification Region Not found")

        specification_details=specification_region.find_all(class_="detail__prop d-flex") if specification_region else []
        specifications_dict={}
        unknown_specifications = []

        logger.debug(f"Parsing Specifications Details - "
                     f"Found {len(list(specification_details))} specifications")

        for specifics in specification_details:
            all_p = specifics.find_all('p')
            if len(all_p) == 2:
                logger.debug("2 p classes found in specifications")
                key = all_p[0].text.strip()
                value = all_p[1].text.strip()
                logger.info(f"Appending Specification - {key} : {value} to list")
                specifications_dict[key]=value
            else:
                for p in all_p:
                    text_value = p.text.strip()

                    logger.warning(
                        f"Specification without a key - storing as 'Unknown_{len(unknown_specifications) + 1}'")

                    unknown_specifications.append(text_value)
                    logger.warning(f"Specification not a dict - appending {p} to list")
                    unknown_specifications.append(text_value)

        if unknown_specifications:
            specifications_dict["Miscellaneous"] = unknown_specifications

        crosses_details=soup.find(class_="detail__plate detail__plate-crosses")
        if not crosses_details:
            logger.error("Crosses Details Not Found")
        crosses_list=[]
        all_cross_details=crosses_details.find_all(class_='detail__prop d-flex') if crosses_details else []

        logger.debug(f"Parsing Crosses Details - "
                     f"Found {len(list(crosses_details))} crosses")

        for cross in all_cross_details:
            all_cross=cross.find_all('div')
            if len(all_cross)==2:
                logger.debug("2 p classes found in crosses")
                if all_cross[0].text.strip()=="Owner":
                    logger.info("Skipping Owner Number Class")
                    continue
                key = all_cross[0].text.strip()
                value = all_cross[1].text.strip()
                logger.info(f"Appending Cross - Owner:{key}, Number:{value} to list ")
                crosses_list.append({"Owner":key, "Number":value})
            else:
                for item in all_cross:
                    logger.warning(f"Cross not a dict - appending {p} to list")
                    crosses_list.append({"Owner":item.text.strip(),"Number":item.text.strip()})

        return url, product_details, product_images, specifications_dict, crosses_list

    def get_data_from_url_using_soup(self, url: str):
        response = self.request(url)
        if response is None:
            return None, None
        logger.debug(
            f'Got the response for {url}, data length: {len(response.text)}'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        search_result_class=soup.find(class_="searchresult")
        if search_result_class:
            logger.info("Sending search result class soup to parse")
            return self.parse_jinku_data_from_soup(search_result_class, url)
        else:
            logger.warning("Sending original soup to parse")
            return self.parse_jinku_data_from_soup(soup, url)

    def get_data_from_url_using_soup_for_df(self, url: str, return_df: bool = False):
        response = self.request(url)
        if response is None:
            return None
        logger.debug(
            f'Got the response for {url}, data length: {len(response.text)}'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        search_result_class = soup.find(class_="searchresult")
        if search_result_class:
            logger.info("Sending search result class soup to parse for DataFrame collection")
            url, product_details, product_images, specifications_dict, crosses_list = self.parse_jinku_data_from_soup(search_result_class, url)
        else:
            logger.warning("Sending original soup to parse for DataFrame collection")
            url, product_details, product_images, specifications_dict, crosses_list = self.parse_jinku_data_from_soup(soup, url)

        formatted_data = self.format_product_details_for_df(url, product_details, product_images, specifications_dict, crosses_list, return_df)
        self.collected_data.extend(formatted_data)


    def process_url(self, url, errored_urls, return_df: bool = False):
        try:
            logger.debug(f"Processing URL - {url}")
            if return_df:
                self.get_data_from_url_using_soup_for_df(url, return_df)
            else:
                self.get_data_from_url_using_soup(url)
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            errored_urls.append(url)

    def main(self, main_url, filename, return_df: bool = False):
        urls = self.get_list_of_urls(main_url)

        if urls is None or len(urls)==0:
            logger.error('Failed to retrieve URLs')
            return pd.DataFrame() if return_df else None

        pdf_urls = []
        valid_urls = []
        errored_urls = []

        for url in urls:
            if not str(url).startswith("http"):
                full_url = main_url + url
            else:
                full_url = url

            logger.info(f"Checking URL - {full_url}")

            if any(ext in full_url for ext in ["pdf", "ebook", "jpg", "png", "jpeg"]):
                logger.info(f"Skipping - {full_url}")
                if 'pdf' in full_url or 'ebook' in full_url:
                    pdf_urls.append(full_url)
                continue

            valid_urls.append(full_url)

        db_worker = None
        if not return_df:
            db_worker = multiprocessing.Process(target=self.insert_to_db_worker, daemon=True)
            db_worker.start()

        self.collected_data = []

        # Using ThreadPoolExecutor for I/O-bound tasks
        with ThreadPoolExecutor(max_workers=MAX_PROCESSES) as executor:
            futures = {executor.submit(self.process_url, url, errored_urls, return_df): url for url in valid_urls}
            for future in as_completed(futures):
                try:
                    future.result()  # Check for exceptions
                except Exception as e:
                    url = futures[future]
                    logger.error(f"Error in thread for {url}: {e}")

        if db_worker:
            db_worker.terminate()
            db_worker.join()

        if not return_df:
            if pdf_urls:
                with open(f"{str(filename).split('.')[0]}_pdf.json", "w") as file:
                    json.dump(pdf_urls, file, indent=4)
                logger.debug(f'PDF urls saved to {str(filename).split(".")[0]}_pdf.json')

            if errored_urls:
                with open(f"{str(filename).split('.')[0]}_errored.json", "w") as file:
                    json.dump(list(errored_urls), file, indent=4)
                logger.debug(f'Errored urls saved to {str(filename).split(".")[0]}_errored.json')

        logger.info("All URLs processed successfully!")

        if return_df:
            if self.collected_data:
                df = pd.DataFrame(self.collected_data)
                self.collected_data = [] # Clear for next run
                return df
            else:
                return pd.DataFrame()


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
    scraper = JinkuRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    _url = 'https://www.cp.pt/passageiros/en/how-to-travel/Useful-information'
    res = scraper.request('https://www.ifconfig.me/all.json')
    print(res.json())
    print(res.status_code)
