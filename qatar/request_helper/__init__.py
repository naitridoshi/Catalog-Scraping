import json
import re

from bs4 import BeautifulSoup

from common.constants import BASIC_HEADERS
from common.request_helper import RequestHelper
import time
import requests

from common.custom_logger import color_string, get_logger

logger, listener = get_logger("QatarRequestHelper")
listener.start()

class QatarRequestHelper(RequestHelper):

    def  __init__(self,proxies:dict=None,headers:dict=BASIC_HEADERS,is_session:bool=False):
        super().__init__(proxies,headers)
        headers = headers.copy() if headers else {}
        self.is_session = is_session
        self.proxies = proxies or {}

        if self.is_session:
            self.session = requests.Session()
            self.session.headers.update(headers)
        else:
            self.headers = headers

    def request(self, url: str, method: str = 'GET', timeout: int = 120,
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
                    "verify": False,
                    "stream": False
                }

                if method.upper() in ('POST', 'PUT', 'PATCH'):
                    if payload:
                        kwargs["data"] = payload
                    elif json:
                        kwargs["json"] = json

                # Only set headers if not using session
                if not use_session and headers:
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

    def get_security_token(self):
        response=self.request("https://qatarcid.com/")
        if response is None:
            return None
        logger.debug("searching for theme_scriptspf")
        match = re.search(r'var\s+theme_scriptspf\s*=\s*(\{.*?\});', response.text, re.DOTALL)
        if not match:
            logger.error("Could not find theme_scriptspf")
            return None

        logger.info(" found theme_scriptspf")
        js_object_str = match.group(1).replace(r'\/', '/')
        theme_scriptspf = json.loads(js_object_str)

        logger.debug("searching for pfget_listitems token")
        security_token = theme_scriptspf.get('pfget_listitems')
        if not security_token:
            logger.error("pfget_listitems token not found.")
            return None

        logger.info(f"Found security token: - {security_token}")

        return security_token

    @staticmethod
    def generate_payload(page_num:int, security_token:str):
        logger.debug(f"generating payload for page - {page_num}")
        return {
            "action": "pfget_listitems",
            "security": security_token,
            "page": str(page_num)
        }

    def get_company_page(self,main_url,payload):
        logger.info(f"getting the company page from - {main_url}")
        response=self.request(main_url,method='POST',payload=payload)
        if response is None:
            return None
        soup=BeautifulSoup(response.text,'html.parser')
        all_company_pages=soup.find_all('div',class_='pflisting-itemband')
        page_list=[company.find('a',href=True).get('href') for company in all_company_pages ]
        logger.info(f"received {len(page_list)} company pages")
        return page_list

    def get_data_from_url_using_soup(self, url: str):
        response=self.request(url)
        if response is None:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        info_soup=soup.find('div',class_='col-lg-4')
        if info_soup is None:
            logger.warning("could not find info soup - sending original soup to parse")
            return self.parse_data(soup,url)
        logger.info("found info soup - sending info soup to parse")
        return self.parse_data(info_soup,url)

    @staticmethod
    def parse_data(soup:BeautifulSoup,url:str):
        logger.debug("parsing data to get details...")
        title_row=soup.find('h1',class_='pf-item-title-text')
        title_row=title_row.getText(strip=True) if title_row else (url.split('/')[-2] if url.endswith('/') else url.split('/')[-1])
        all_info_rows=soup.find_all('div',class_='pfdetailitem-subelement pf-onlyitem clearfix')
        info_details={}
        for info_row in all_info_rows:
            title=info_row.find('span',class_='pf-ftitle')
            title=title.getText(strip=True) if title else ''
            detail=info_row.find('span',class_='pfdetail-ftext')
            detail=detail.getText(strip=True) if detail else ''
            logger.debug(f"found title - {title} - found detail - {detail}")
            info_details.update({title:detail})
            logger.debug(f"Found {len(info_details)} details for company {title_row}")
        return {title_row:info_details}

    def main(self, main_url, filename, page_num):
        try:
            security_token=self.get_security_token()
            if security_token is None:
                logger.error("Could not get the security token...")
                return
            payload=self.generate_payload(security_token=security_token,page_num=page_num)
            company_pages=self.get_company_page(main_url,payload)
            if company_pages is None:
                logger.error("Could not find the company page")
                return None
            company_list=[]
            for company in company_pages:
                logger.info(f"getting data from url for company - {company}")
                company_list.append(self.get_data_from_url_using_soup(company))
            logger.info(f"saving data to file {filename}")
            with open(filename,'w') as f:
                json.dump(company_list,f,indent=2)
            logger.info(f"completed scraping page - {page_num}")
        except Exception as e:
            logger.error(f"Error Occurred in entire process - {str(e)}",exc_info=True)

if __name__ == '__main__':
    BASIC_HEADERS.update({
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://qatarcid.com',
    'X-Requested-With': 'XMLHttpRequest',
})
    request_helper=QatarRequestHelper(is_session=True, headers=BASIC_HEADERS)
    response=request_helper.request("https://www.google.com")
    if response:
        print(response.text)