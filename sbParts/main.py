import asyncio
import pandas as pd
import os
import json
from common.custom_logger import get_logger

from common.constants import BASIC_HEADERS
from sbParts.constants import HEADERS
from sbParts.request_helper import SbPartsRequestHelper

logger, listener = get_logger("SbPartsScraper")
listener.start()


async def run_sbparts_scraper_and_return_df(product_id:str) -> pd.DataFrame:
    logger.info("Starting SB Parts scraper for Streamlit app...")
    scraper = SbPartsRequestHelper(headers=HEADERS)

    output_dir = "files/sbParts"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{output_dir}/sbparts_temp_data.json"

    try:
        df = await scraper.main(filename=output_filename, return_df=True)
        logger.info("Completed Scraping for SB Parts .... ")
        return df

    except Exception as e:
        logger.error(f"An error occurred while scraping SB Parts - {str(e)}")
        return pd.DataFrame()


async def run_sbparts_scraper_for_part_number(part_number: str) -> pd.DataFrame:
    logger.info(f"Starting SB Parts scraper for part number: {part_number}...")
    scraper = SbPartsRequestHelper(headers=HEADERS)

    try:
        # 1. Collect part number data
        collected_parts = await scraper.collect_part_number(part_number)
        if not collected_parts:
            logger.warning(f"No parts found for part number: {part_number}")
            return pd.DataFrame()

        # 2. Process collected parts and get a DataFrame
        df = await scraper.process_collected_parts(collected_parts, return_df=True)
        logger.info(f"Completed scraping for SB Parts part number: {part_number}")
        return df

    except Exception as e:
        logger.error(f"An error occurred while scraping SB Parts for part number {part_number} - {str(e)}")
        return pd.DataFrame()


if __name__ == '__main__':


    scraper = SbPartsRequestHelper(
        # proxies=DATA_CENTER_PROXIES,
        headers=HEADERS
    )

    asyncio.run(scraper.main(filename='autoSparePartsCatalog.sbparts_parts_data.json'))