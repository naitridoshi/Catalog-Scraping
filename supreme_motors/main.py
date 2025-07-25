import asyncio
from supreme_motors.request_helper import SupremeMotorsRequestHelper
from common.custom_logger import get_logger

logger, listener = get_logger("SupremeMotorsMain")
listener.start()


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