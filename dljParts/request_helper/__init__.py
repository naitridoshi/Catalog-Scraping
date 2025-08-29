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
from common.request_helper import RequestHelper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger, listener = get_logger("DLJRequestHelper")
listener.start()

dubai_tz = pytz.timezone("Asia/Dubai")

class DLJRequestHelper(RequestHelper):

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
    def create_dataframe(data_list, max_oem_count):
        if not data_list:
            return pd.DataFrame()
        headers = [f"OEM NO. {i + 1}" for i in range(max_oem_count)] + ["CAR NAME", "PRODUCT", "YEAR", "POSITION", "PIC"]
        df = pd.DataFrame(data_list, columns=headers)
        return df

    @staticmethod
    def save_to_excel(df, filename, url):
        try:
            if df.empty:
                logger.warning("No data to save. The DataFrame is empty.")
                raise Exception("EMPTY DATA")

            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")

            sheet_name = f"DLJ-{str(url.split('=')[-1]).upper()[:25]}"
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'center',
                    'fg_color': '#4F81BD',
                    'font_color': 'white',
                    'border': 1
                })

                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                cell_format = workbook.add_format({
                    'border': 1,
                    'text_wrap': True,
                    'valign': 'top'
                })

                for row_num in range(1, len(df) + 1):
                    for col_num in range(len(df.columns)):
                        worksheet.write(row_num, col_num, df.iloc[row_num - 1, col_num], cell_format)

                for i, column in enumerate(df.columns):
                    max_len = max(df[column].astype(str).map(len).max(), len(column))
                    adjusted_width = min(max_len + 2, 30)
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

    def main(self, main_url, filename=None, return_df=False):
        raw_data, max_oem_count = self.get_data_from_url_using_soup(main_url)
        
        if not raw_data:
            logger.error("Failed to get data or no data found.")
            return pd.DataFrame() if return_df else None

        df = self.create_dataframe(raw_data, max_oem_count)

        if return_df:
            return df
        else:
            if filename:
                self.save_to_excel(df, filename, main_url)
            else:
                logger.error("Filename not provided for saving.")

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
    scraper = DLJRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers={}
    )
    _url = 'https://www.cp.pt/passageiros/en/how-to-travel/Useful-information'
    res = scraper.request('https://www.ifconfig.me/all.json')
    print(res.json())
    print(res.status_code)