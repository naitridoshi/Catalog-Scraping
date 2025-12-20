import gc
import json
import multiprocessing
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

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

    def scrape_each_product_cards(self, cards: List[str]) -> List[Dict[str, Any]]:
        all_details: List[Dict[str, Any]] = []

        for card in cards:
            card_details: Dict[str, Any] = {}
            response = self.request(card)
            if response is None:
                logger.error(f"Error fetching engine related data for {card}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            model_and_class = soup.find("button", class_="model-title")
            if model_and_class:
                model_info = model_and_class.text.split("»")

                brand = model_info[0].strip()

                # Only the first meaningful token (e.g., "TOYOTA"), nothing after it.
                # Example chunk: " TOYOTA \n\xa0\xa0\xa0\xa0\n 01.74~12.22"
                model = model_info[1].strip().split()[0] if len(model_info) > 1 else None

                card_details["brand"] = brand
                card_details["class"] = model

            vehicle_info_class = soup.find(class_="vehicle-info")
            if vehicle_info_class:
                # Mod:
                p = vehicle_info_class.find("p")
                if p and p.find("strong"):
                    label = p.find("strong").get_text(strip=True)
                    value = p.get_text(strip=True).replace(label, "").strip().strip("[]")

                    if label == "Mod:":
                        vehicle_mods = [v.strip() for v in value.split(",") if v.strip()]
                        card_details["mod"] = vehicle_mods

                # Engine info
                engine_info_class = vehicle_info_class.find("div", class_="d-flex")
                if engine_info_class:
                    for p in engine_info_class.find_all("p"):
                        strong = p.find("strong")
                        if not strong:
                            continue
                        label = strong.get_text(strip=True)
                        value = p.get_text(strip=True).replace(label, "").strip().strip("[]")

                        if label == "Eng cc:":
                            engine_ccs = [v.strip() for v in value.split(",") if v.strip()]
                            card_details["eng_cc"] = engine_ccs
                        elif label == "Eng code:":
                            engine_codes = [v.strip() for v in value.split(",") if v.strip()]
                            card_details["eng_code"] = engine_codes

            all_details.append(card_details)

        return all_details

    def fetch_engine_related_data(self, jinku_product_id: str, jinku_url: str) -> Optional[Dict[str, Any]]:
        response = self.request(jinku_url)
        if response is None:
            logger.error(f"Error fetching engine related data for {jinku_product_id}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        accordian = soup.find(id="accordionSearchResult")
        if accordian is None:
            logger.warning(f"No accordion found for {jinku_product_id}")
            return {
                "jinku_product_id": jinku_product_id,
                "jinku_url": jinku_url,
                "model_and_engine_details": [],
            }

        cards = accordian.find_all(class_="card")
        all_cards: List[str] = []

        for card in cards:
            link = card.find("a")
            if link and link.has_attr("href"):
                all_cards.append(link["href"])

        model_details = self.scrape_each_product_cards(all_cards)

        all_details: Dict[str, Any] = {
            "jinku_product_id": jinku_product_id,
            "jinku_url": jinku_url,
            "model_and_engine_details": model_details,
        }
        return all_details

    def _load_jobs_from_json(self, input_json_path: str) -> List[Dict[str, str]]:
        """
        Expected input JSON formats (either is fine):

        1) A list:
        [
          {"jinku_product_id": "123", "jinku_url": "https://..."},
          ...
        ]

        2) A dict with a key holding the list:
        {"items": [ ...same objects... ]}
        """
        with open(input_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # common container keys
            for key in ("products", "items", "data", "records", "results"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                raise ValueError(
                    "Input JSON must be a list OR a dict containing a list under one of: "
                    "items/data/records/results"
                )
        else:
            raise ValueError("Input JSON must be a list or a dict containing a list.")

        jobs: List[Dict[str, str]] = []
        for i, row in enumerate(items):
            if not isinstance(row, dict):
                logger.warning(f"Skipping non-dict item at index {i}: {row!r}")
                continue
            pid = row.get("jinku_product_id")
            url = row.get("jinku_url")
            if not pid or not url:
                logger.warning(f"Skipping item missing jinku_product_id/jinku_url at index {i}: {row!r}")
                continue
            jobs.append({"jinku_product_id": str(pid), "jinku_url": str(url)})

        return jobs

    def fetch_all_from_json_multithreaded(
            self,
            input_json_path: str,
            output_json_path: str,
            max_workers: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Reads input JSON (list of product ids + urls),
        concurrently calls fetch_engine_related_data,
        writes complete results to output_json_path.
        Returns the collected results too.
        """
        jobs = self._load_jobs_from_json(input_json_path)
        logger.info(f"Loaded {len(jobs)} jobs from {input_json_path}")

        results: List[Dict[str, Any]] = []
        # Keep a small map for debugging failures
        failures: List[Dict[str, str]] = []

        def worker(job: Dict[str, str]) -> Optional[Dict[str, Any]]:
            return self.fetch_engine_related_data(job["jinku_product_id"], job["jinku_url"])

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(worker, job): job for job in jobs}

            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    data = future.result()
                    if data is None:
                        failures.append(job)
                        continue
                    results.append(data)
                except Exception as e:
                    logger.exception(f"Failed job {job} with error: {e}")
                    failures.append(job)

        # Write output
        out_payload = {
            "count": len(results),
            "failed_count": len(failures),
            "failed": failures,  # keep this if you want; remove if you only want successes
            "results": results,  # complete data
        }

        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(out_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"Wrote {len(results)} results to {output_json_path}. Failures: {len(failures)}")
        return results

if __name__ == '__main__':
    scraper = JinkuRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        # headers={}
    )

    input_file="unique_jinku_product_ids.json"
    output_file="complete_engine_related_data.json"
    # _jinku_product_id="BM21012"
    # _jinku_url="https://jikiu.com/catalogue/49942991"
    # all_details =scraper.fetch_engine_related_data(_jinku_product_id, _jinku_url)
    scraper.fetch_all_from_json_multithreaded(
        input_json_path=input_file,
        output_json_path=output_file,
        max_workers=100,
    )
    # print(all_details)
