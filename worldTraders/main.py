from common.custom_logger import get_logger
from worldTraders.request_helper import RequestHelper
from worldTraders.constants import IPC_NET_SEARCH_URL, IPC_NET_GET_DETAILS_URL
import pandas as pd
import os

logger, listener = get_logger("WorldTradersScraper")
listener.start()



def run_world_traders_scraper_and_return_df() -> pd.DataFrame:
    logger.info("Starting World Traders scraper for Streamlit app...")
    request_helper = RequestHelper()
    all_data_frames = []

    for current_page in range(1, 49): # Scrape pages 1 to 48
        SEARCH_URL = f"{IPC_NET_SEARCH_URL}/{current_page}/?pid=0&aid=0&cid=0"
        logger.info(f"Getting Data for page - {current_page} ({SEARCH_URL})")

        output_dir = "files/worldTraders"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"{output_dir}/world_traders_page_{current_page}_temp.xlsx"

        try:
            request_helper.main(SEARCH_URL, output_filename)
            logger.info(f"Completed Scraping for page - {current_page} .... ")

            if os.path.exists(output_filename):
                df = pd.read_excel(output_filename)
                all_data_frames.append(df)
                os.remove(output_filename) # Clean up temporary file
            else:
                logger.warning(f"Output file not found for page {current_page}: {output_filename}")

        except Exception as e:
            logger.error(f"An error occurred while scraping for page - {current_page} - {str(e)}")
            # Continue to next page even if one fails

    if all_data_frames:
        combined_df = pd.concat(all_data_frames, ignore_index=True)
        return combined_df
    else:
        return pd.DataFrame()


if __name__ == '__main__':
    request_helper = RequestHelper()

    page=1

    for current_page in range(page, 49):
        SEARCH_URL = f"{IPC_NET_SEARCH_URL}/{current_page}/?pid=0&aid=0&cid=0"
        logger.info(f"Getting Data for query - {SEARCH_URL}")
        try:
            request_helper.main(SEARCH_URL,f"files/ipcNet/importers_and_exporters.xlsx")
            logger.info(f"Completed Scraping for code - {SEARCH_URL} .... ")
        except Exception as e:
            logger.error(f"Empty data found for query - {SEARCH_URL} - {str(e)}")
