import json
import re
import time

import requests
import urllib3
from bs4 import BeautifulSoup

# from common.config import DATA_CENTER_PROXIES
from common.constants import BASIC_HEADERS
from common.custom_logger import color_string, get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("RequestHelper")
listener.start()


class RequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers

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

    def main(self, main_url,filename):
        urls = self.get_list_of_urls(main_url)
        if urls is None or len(urls)==0:
            logger.error('Failed to retrieve URLs')
            return
        data = []
        pdf_urls=[]

        for url in urls:
            if not str(url).startswith("http"):
                full_url = main_url + url
            else:
                full_url=url

            logger.debug(f"Getting url - {full_url}")

            if 'pdf' in url or 'ebook' in url:
                logger.info(f"Skipping - {full_url}")
                pdf_urls.append(full_url)
                continue

            if 'jpg' in url or 'png' in url or 'jpeg' in url:
                logger.info(f"Skipping - {full_url}")
                continue

            _data, _cleaned_data = self.get_data_from_url_using_soup(full_url)
            data.append(
                {
                    'url': full_url,
                    'heading': full_url.split('/')[-1],
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
