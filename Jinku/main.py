import os
import time

from Jinku.constants import JINKU_PRODUCT_URL, JINKU_PRODUCT_URL_PARAMS
from common.custom_logger import get_logger
from common.request_helper import RequestHelper

logger, listener = get_logger("Jinku Scraper")
listener.start()



if __name__ == '__main__':
    request_helper = RequestHelper()

    LETTER="a"  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE

    logger.info(f"Getting Data for code - {LETTER}")
    main_url = f"{JINKU_PRODUCT_URL}?product_id={LETTER}"

    request_helper.main(main_url,f"files/jinku_products_{LETTER}.json")

    logger.info(f"Completed Scraping for code - {LETTER} .... ")

    # for code in range(ord('a'), ord('a') + 1):
    #     logger.info(f"Getting Data for code - {chr(code)}")
    #     main_url=f"{JINKU_PRODUCT_URL}?product_id={chr(code)}"
    #     request_helper.main(main_url,"files/jinku_products.json")
    #     logger.info(f"Completed Scraping...")