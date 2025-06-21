import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.errors import NonPrintableDefect

import requests
import urllib3
from bs4 import BeautifulSoup

# from ask_gemini import response
from common.constants import BASIC_HEADERS
from common.custom_logger import color_string, get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import curl
logger, listener = get_logger("RequestHelper")
listener.start()


class RequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers

    def request(self, url: str, method: str = 'GET', timeout: int = 10,
                params: dict = None, json: dict | list = None,
                headers: dict = None, payload=None):
        logger.debug(f"Requesting {url} ...")
        use_session = self.is_session

        # Choose the correct method
        if use_session:
            logger.info("Using sessions Request .... ")
            if method.upper() == 'GET':
                request_method = self.session.get
            elif method.upper() == 'POST':
                request_method = self.session.post
            elif method.upper() == 'PUT':
                request_method = self.session.put
            elif method.upper() == 'PATCH':
                request_method = self.session.patch
            elif method.upper() == 'DELETE':
                request_method = self.session.delete
            else:
                request_method = lambda *args, **kwargs: self.session.request(method=method, *args, **kwargs)
        else:
            request_method = requests.request
            if headers is None:
                headers = self.headers

        for try_request in range(1, 5):
            start_time = time.time()
            try:
                kwargs = {
                    "url": url,
                    "params": params,
                    "proxies": self.proxies,
                    "timeout": timeout,
                    "verify": True,
                    "stream": False
                }

                if method.upper() in ('POST', 'PUT', 'PATCH'):
                    if payload:
                        kwargs["data"] = payload
                    elif json:
                        kwargs["json"] = json

                # Always set headers if provided, even for session
                if headers:
                    kwargs["headers"] = headers

                response = request_method(**kwargs)

                time_taken = f'{time.time() - start_time:.2f} seconds'
                if response.status_code == 200:
                    logger.debug(
                        f'Try: {try_request}, '
                        f'Status Code: {response.status_code}, '
                        f'Response Length: {len(response.text) / 1024 / 1024:.2f} MB, '
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
                    f"{color_string(f'{time.time() - start_time:.2f} seconds')}, "
                    f"Error: {repr(err)}"
                )
            time.sleep(1)  # Add delay between retries

    def get_list_of_urls(self, url: str):
        response = self.request(url)
        if response is None:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        urls = set([a['href'] for a in soup.find_all('a', href=True) if ("gms-store" in str(a['href']) and str(a['href']).startswith("http") )or str(a['href']).startswith("/")])
        logger.debug(f'Extracted {len(urls)} URLs')
        return urls

    def get_data_from_url_using_soup(self, url: str):
        response = self.request(url)
        if response is None:
            return None, None
        logger.debug(
            f'Got the response for {url}, data length: {len(response.text)}'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.text.strip().replace('\n', '').replace('\t', '').replace(
            '\r',
            ''
        ).replace('\v', '').replace('\f', '').replace('\xa0', '')
        cleaned_text = re.sub(r'\s+', ' ', soup.text.strip())
        return text, cleaned_text

    def main(self, main_url, filename):
        main_list_of_urls = set()
        processed_urls = set()
        lock = threading.Lock()

        main_list_of_urls.update(self.get_list_of_urls(main_url))
        if not main_list_of_urls:
            logger.error("Failed to retrieve URLs")
            return

        data = []
        pdf_urls = []

        def process_url(url):
            """Function to process a single URL"""
            if not str(url).startswith("http"):
                full_url = main_url + url
            else:
                full_url = url

            logger.debug(f"Getting URL - {full_url}")

            if any(ext in url for ext in ["pdf", "ebook", "download"]):
                logger.info(f"Skipping - {full_url}")
                with lock:
                    pdf_urls.append(full_url)
                return None

            if any(ext in url for ext in ["jpg", "png", "jpeg","twitter","facebook","instagram","reddit","pinterest","yelp","youtube"]):
                logger.info(f"Skipping - {full_url}")
                return None

            try:
                _data, _cleaned_data = self.get_data_from_url_using_soup(full_url)
                result = {
                    "url": full_url,
                    "heading": full_url.split("/")[-1],
                    "data": _data,
                    "cleanedData": _cleaned_data,
                }
            except Exception as e:
                logger.error(f"Failed to fetch data from {full_url}: {e}")
                return None

            try:
                fresh_urls = set(self.get_list_of_urls(full_url))
            except Exception as e:
                fresh_urls = set()
                logger.error(f"Error fetching URLs from {full_url}: {e}")

            with lock:
                main_list_of_urls.update(fresh_urls - processed_urls)
                processed_urls.add(url)
                data.append(result)

        with ThreadPoolExecutor(max_workers=5) as executor:
            while main_list_of_urls:
                futures = {
                    executor.submit(process_url, url): url for url in list(main_list_of_urls)
                }
                main_list_of_urls.clear()

                for future in as_completed(futures):
                    future.result()


        with open(filename, "w") as file:
            json.dump(data, file, indent=4)
        logger.debug(f"Data saved to {filename}")

        with open(f"{filename.rsplit('.', 1)[0]}_pdf.json", "w") as file:
            json.dump(pdf_urls, file, indent=4)
        logger.debug(f"Data saved to {filename.rsplit('.', 1)[0]}_pdf.json")


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

    def get_list_of_sitemap_urls(self,url):
        response=self.request(url)
        soup=BeautifulSoup(response.text,'html.parser')
        all_sitemaps=soup.find_all('sitemap')
        sitemap_list=[]
        for sitemap in all_sitemaps:
            sitemap_list.append(sitemap.find('loc').text)
        return sitemap_list

    def get_urls_from_sitemaps(self,url):
        response=self.request(url)
        soup=BeautifulSoup(response.text,'html.parser')
        all_urls=soup.find_all('url')
        list_of_all_urls=set()
        for url in all_urls:
            list_of_all_urls.append(url.find('loc').text)
        return list_of_all_urls

    def main_sitemap(self,sitemap_url:str,filename:str):
        sitemap_list=self.get_list_of_urls(sitemap_url)
        main_list_of_urls=[]
        pdf_urls=[]
        data=[]
        for sitemap in sitemap_list:
            main_list_of_urls.append(self.get_urls_from_sitemaps())

        for url in main_list_of_urls:
            if 'pdf' in url or 'ebook' in url or 'download' in url:
                logger.info(f"Skipping - {url}")
                pdf_urls.append(url)
                continue

            if 'jpg' in url or 'png' in url or 'jpeg' in url:
                logger.info(f"Skipping - {url}")
                continue

            _data, _cleaned_data = self.get_data_from_url_using_soup(url)
            data.append(
                {
                    'url': url,
                    'heading': url.split('/')[-1],
                    'data': _data,
                    'cleanedData': _cleaned_data
                }
            )

        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
        logger.debug(f'Data saved to {filename}')

        with open(f"{str(filename).split('.')[0]}_pdf.json", "w") as file:
            json.dump(pdf_urls, file, indent=4)
        logger.debug(f'Data saved to {str(filename).split(".")[0]}_pdf.json')



if __name__ == '__main__':
    headers = {
        'accept': 'text/html, */*; q=0.01',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://qatarcid.com',
        'priority': 'u=1, i',
        'referer': 'https://qatarcid.com/?jobskeyword=&field_company=&field_listingtype=&geolocation=&pointfinder_google_search_coord=&pointfinder_google_search_coord_unit=Mile&pointfinder_radius_search=&ne=&ne2=&sw=&sw2=&CR_NO=&QCCI_MEM_NO=&s=&serialized=1&action=pfs',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'Cookie': 'PHPSESSID=ac7dc2c95bd2cb8cc5a9fa606837a617; PHPSESSID=ccd35549eefa17bac35e62f171ba6cf9'
    }
    scraper = RequestHelper(headers=headers)
    _url = "https://qatarcid.com/wp-content/plugins/pointfindercoreelements/includes/pfajaxhandler.php"
    payload="action=pfget_listitems&act=search&dt%5Bjobskeyword%5D=&dt%5Bfield_company%5D=&dt%5Bfield_listingtype%5D=&dt%5Bgeolocation%5D=&dt%5Bpointfinder_google_search_coord%5D=&dt%5Bpointfinder_google_search_coord_unit%5D=Mile&dt%5Bpointfinder_radius_search%5D=&dt%5Bne%5D=&dt%5Bne2%5D=&dt%5Bsw%5D=&dt%5Bsw2%5D=&dt%5BCR_NO%5D=&dt%5BQCCI_MEM_NO%5D=&dt%5Bs%5D=&dt%5Bserialized%5D=1&dt%5Baction%5D=pfs&dtx%5B0%5D%5Bname%5D=post_tags&dtx%5B0%5D%5Bvalue%5D=&dtx%5B1%5D%5Bname%5D=pointfinderltypes&dtx%5B1%5D%5Bvalue%5D=&dtx%5B2%5D%5Bname%5D=pointfinderlocations&dtx%5B2%5D%5Bvalue%5D=&dtx%5B3%5D%5Bname%5D=pointfinderconditions&dtx%5B3%5D%5Bvalue%5D=&dtx%5B4%5D%5Bname%5D=pointfinderitypes&dtx%5B4%5D%5Bvalue%5D=&dtx%5B5%5D%5Bname%5D=pointfinderfeatures&dtx%5B5%5D%5Bvalue%5D=&ne=&sw=&ne2=&sw2=&cl=&grid=&pfg_orderby=&pfg_order=&pfg_number=&pfcontainerdiv=.pfsearchresults&pfcontainershow=.pfsearchgridview&page=&from=halfmap&security=6f5953518f&pflat=undefined&pflng=undefined&ohours="
    res = scraper.request(_url,payload=payload)
    print(res.text)

