import json
import multiprocessing
import os
import re
import time
import pandas as pd
import pytz
import requests
import urllib3
from bs4 import BeautifulSoup
from itertools import product

# from common.config import DATA_CENTER_PROXIES
from common.constants import BASIC_HEADERS, BATCH_SIZE, MAX_PROCESSES
from common.custom_logger import color_string, get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("DLJRequestHelper")
listener.start()

dubai_tz = pytz.timezone("Asia/Dubai")

class RequestHelper:
    def __init__(self, proxies: dict = None, headers: dict = BASIC_HEADERS):
        self.proxies = proxies
        self.headers = headers
        self.shared_list = multiprocessing.Manager().list()

    def request(self, url: str, method: str = 'GET', timeout: int = 30,params:dict=None,json:dict | list =None,headers:dict=None):
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

    @staticmethod
    def parse_dlj_data(soup: BeautifulSoup):
        parsed_data = []
        max_oem_count = 0

        try:
            table = soup.find('table')
            if not table:
                logger.warning("No table found in the provided soup object.")
                return parsed_data

            all_tr = table.find_all('tr')
            if not all_tr:
                logger.warning("No <tbody> elements found in the table.")
                return parsed_data

            logger.debug(f"Found {len(all_tr)} rows to parse ...")
            for count, tr in enumerate(all_tr):
                if count == 0:
                    continue  # skip header

                tds = [td.get_text(separator="\n", strip=True) for td in tr.find_all('td')]
                if not tds:
                    continue

                oem_numbers = tds[0].split("\n")
                rest_of_data = tds[1:]

                max_oem_count = max(max_oem_count, len(oem_numbers))
                parsed_data.append((oem_numbers, rest_of_data))

            # Normalize rows: pad OEMs so all rows align properly
            final_data = []
            for oems, rest in parsed_data:
                padded_oems = oems + [''] * (max_oem_count - len(oems))
                final_data.append(padded_oems + rest)

            logger.info(f"Successfully parsed {len(final_data)} normalized records from the table.")

            return final_data, max_oem_count

        except Exception as e:
            logger.error(f"Error occurred while parsing DLJ data: {str(e)}")
            return [], None

    @staticmethod
    def save_to_excel(data_list, filename, url, max_oem_count):
        try:
            if not data_list:
                logger.warning("No data to save. The list is empty.")
                raise Exception("EMPTY DATA")

            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")

            headers = [f"OEM NO. {i + 1}" for i in range(max_oem_count)] + ["CAR NAME", "PRODUCT", "YEAR", "POSITION",
                                                                            "PIC"]
            df = pd.DataFrame(data_list, columns=headers)

            sheet_name = f"DLJ-{str(url.split('=')[-1]).upper()[:25]}"
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # Header Format: Bold, White Text, Blue Background
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'center',
                    'fg_color': '#4F81BD',  # background color
                    'font_color': 'white',  # text color
                    'border': 1
                })

                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Cell Format: Border, Text Wrap
                cell_format = workbook.add_format({
                    'border': 1,
                    'text_wrap': True,
                    'valign': 'top'
                })

                # Apply cell format to the entire data range
                for row_num in range(1, len(df) + 1):
                    for col_num in range(len(df.columns)):
                        worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], cell_format)

                # Auto-adjust column width
                for i, column in enumerate(df.columns):
                    max_len = max(df[column].astype(str).map(len).max(), len(column))
                    adjusted_width = min(max_len + 2, 30)  # Cap width to 30 characters
                    worksheet.set_column(i, i, adjusted_width)

            logger.info(f"Data successfully saved and prettified to {filename}")

        except Exception as e:
            logger.error(f"Error occurred while saving data to Excel: {str(e)}")

    def get_data_from_url_using_soup(self, url: str):
        response = self.request(url)
        if response is None:
            return None, None
        logger.debug(
            f'Got the response for {url}, data length: {len(response.text)}'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        excel_class=soup.find('div',class_="row aos-init aos-animate")
        if excel_class:
            logger.info("Sending excel class soup to parse")
            return self.parse_dlj_data(excel_class)
        else:
            logger.warning("Sending original soup to parse")
            return self.parse_dlj_data(soup)

    def main(self, main_url,filename):
        raw_data, max_oem_count = self.get_data_from_url_using_soup(main_url)
        if max_oem_count:
            self.save_to_excel(raw_data,filename,main_url,max_oem_count)
        else:
            logger.error("Failed to save...")

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
