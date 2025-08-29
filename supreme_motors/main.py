import asyncio
import pandas as pd
import os
import json
from supreme_motors.request_helper import SupremeMotorsRequestHelper
from common.custom_logger import get_logger

logger, listener = get_logger("SupremeMotorsMain")
listener.start()


async def run_supreme_motors_scraper_and_return_df() -> pd.DataFrame:
    logger.info("Starting Supreme Motors scraper for Streamlit app...")
    scraper = SupremeMotorsRequestHelper()

    try:
        results = await scraper.main()
        logger.info("Completed Scraping for Supreme Motors .... ")

        return pd.DataFrame(results)

    except Exception as e:
        logger.error(f"An error occurred while scraping Supreme Motors - {str(e)}")
        return pd.DataFrame()


if __name__ == "__main__":
    try:
        logger.info("Starting scraping.....")
        scraper = SupremeMotorsRequestHelper()
        asyncio.run(scraper.main())
        logger.info("Scraping completed......")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        listener.stop()
        logger.info("Listener stopped")