import gc
import json
import multiprocessing
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor
from datetime import datetime, timezone

import psutil
import requests
import urllib3
from bs4 import BeautifulSoup

# from common.config import DATA_CENTER_PROXIES
from common.constants import BASIC_HEADERS, BATCH_SIZE, MAX_PROCESSES
from common.custom_logger import color_string, get_logger
from common.db import jinku_products_collection

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("RequestHelper")
listener.start()


class RequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = multiprocessing.Manager().list()

    def request(self, url: str, method: str = 'GET', timeout: int = 10,params:dict=None,json:dict | list =None,headers:dict=None):
        logger.debug(f"Requesting {url} ...")
        for try_request in range(1, 5):
            start_time = time.time()
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
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
                        f'Text: {response.text} '
                        f'Time Taken: {color_string(time_taken)}.'
                    )
            except Exception as err:
                logger.error(
                    f'ERROR OCCURRED - {try_request}: Time Taken '
                    f"{color_string(f'{time.time() - start_time:.2f} seconds')}"
                    f', Error: {err}'
                )

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
            cross_doc["createdAt"]= datetime.now(timezone.utc)
            cross_doc["updatedAt"] = datetime.now(timezone.utc)
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

        return self.format_and_store_product_details_in_database(url,product_details, product_images, specifications_dict, crosses_list)

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


    def process_url(self, url,errored_urls):
        try:
            logger.debug(f"Processing URL - {url}")
            self.get_data_from_url_using_soup(url)
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            errored_urls.append(url)

    def main(self, main_url,filename):
        urls = self.get_list_of_urls(main_url)

        if urls is None or len(urls)==0:
            logger.error('Failed to retrieve URLs')
            return

        pdf_urls = []
        valid_urls = []
        # Use a Manager list for errored URLs in multiprocessing
        manager = multiprocessing.Manager()
        errored_urls = manager.list()

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

        # Start the DB worker process for batch inserts
        db_worker = multiprocessing.Process(target=self.insert_to_db_worker, daemon=True)
        db_worker.start()

        if not self.check_memory():
            logger.warning("Low memory detected, running sequentially.")
            for url in valid_urls:
                self.process_url(url, errored_urls)
        else:
            with ProcessPoolExecutor(max_workers=MAX_PROCESSES) as executor:
                futures = {executor.submit(self.process_url, url, errored_urls): url for url in valid_urls}
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        future.result()
                        logger.info(f"Successfully processed {url}")
                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}")
                        errored_urls.append(url)

        db_worker.terminate()
        db_worker.join()



        if pdf_urls:
            with open(f"{str(filename).split('.')[0]}_pdf.json", "w") as file:
                json.dump(pdf_urls, file, indent=4)
            logger.debug(f'PDF urls saved to {str(filename).split(".")[0]}_pdf.json')

        if errored_urls:
            with open(f"{str(filename).split('.')[0]}_errored.json", "w") as file:
                json.dump(list(errored_urls), file, indent=4)
            logger.debug(f'Errored urls saved to {str(filename).split(".")[0]}_errored.json')

        logger.info("All URLs processed successfully!")


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
    scraper = RequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    _url = 'https://www.cp.pt/passageiros/en/how-to-travel/Useful-information'
    res = scraper.request('https://www.ifconfig.me/all.json')
    print(res.json())
    print(res.status_code)
