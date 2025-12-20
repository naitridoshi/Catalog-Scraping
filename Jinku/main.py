import os
import time
import pandas as pd
import json

from Jinku.constants import JINKU_PRODUCT_URL
from common.custom_logger import get_logger
from Jinku.request_helper import JinkuRequestHelper

logger, listener = get_logger("Jinku Scraper")
listener.start()

def run_jinku_scraper(product_id: str) -> pd.DataFrame:
    """
    Runs the Jinku scraper for a given product ID.

    Args:
        product_id: The product ID to search for.

    Returns:
        A pandas DataFrame containing the scraped data, or an empty DataFrame if no data is found.
    """
    request_helper = JinkuRequestHelper()

    logger.info(f"Getting Data for code - {product_id}")
    main_url = f"{JINKU_PRODUCT_URL}?product_id={product_id}"

    output_dir = "files/Jinku"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{output_dir}/jinku_products_{product_id}.json"

    try:
        df = request_helper.main(main_url, output_filename, return_df=True)
        logger.info(f"Completed Scraping for code - {product_id} .... ")
        return df

    except Exception as e:
        logger.error(f"An error occurred while scraping for product ID - {product_id} - {str(e)}")
        return pd.DataFrame()


if __name__ == '__main__':
    LETTER = "40"  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE
    run_jinku_scraper(LETTER)
