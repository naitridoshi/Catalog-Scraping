from common.constants import BASIC_HEADERS
from common.custom_logger import get_logger
from qatar.request_helper import QatarRequestHelper
import pandas as pd
import os
import json

logger, listener = get_logger("QatarScraper")
listener.start()



def run_qatar_scraper_and_return_df(page_num: int) -> pd.DataFrame:
    logger.info(f"Starting Qatar CID scraper for Streamlit app for page: {page_num}")
    headers = BASIC_HEADERS.copy()
    headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://qatarcid.com',
        'X-Requested-With': 'XMLHttpRequest',
    })
    request_helper = QatarRequestHelper(is_session=True, headers=headers)

    output_dir = "files/qatar"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{output_dir}/qatar_page_{page_num}_temp.json"

    try:
        request_helper.main("https://qatarcid.com/wp-content/plugins/pointfindercoreelements/includes/pfajaxhandler.php",
                            output_filename, page_num)
        logger.info(f"Completed Scraping for page - {page_num} .... ")

        if os.path.exists(output_filename):
            with open(output_filename, 'r') as f:
                data = json.load(f)
            df = pd.json_normalize(data)
            os.remove(output_filename) # Clean up temporary file
            return df
        else:
            logger.warning(f"Output file not found: {output_filename}")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"An error occurred while scraping for page - {page_num} - {str(e)}")
        return pd.DataFrame()


if __name__ == '__main__':
    headers=BASIC_HEADERS.update({
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://qatarcid.com',
    'X-Requested-With': 'XMLHttpRequest',
})
    request_helper = QatarRequestHelper(is_session=True,headers=headers)

    PAGE_NUM=1  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE

    logger.info(f"Getting Data for page - {PAGE_NUM}")
    try:
        request_helper.main("https://qatarcid.com/wp-content/plugins/pointfindercoreelements/includes/pfajaxhandler.php",
                            f"files/qatar/{PAGE_NUM}.json",PAGE_NUM)

        logger.info(f"Completed Scraping for code - {PAGE_NUM} .... ")
    except Exception as e:
        logger.error(f"Empty data found for query - {PAGE_NUM} - {str(e)}")
