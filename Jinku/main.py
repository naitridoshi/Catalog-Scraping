from Jinku.constants import JINKU_PRODUCT_URL, JINKU_PRODUCT_URL_PARAMS
from common.custom_logger import get_logger
from common.request_helper import RequestHelper

logger, listener = get_logger("Jinku Scraper")
listener.start()

request_helper = RequestHelper()

if __name__ == '__main__':
    logger.info(f"Getting Data for code - a")
    main_url = f"{JINKU_PRODUCT_URL}?product_id=a"
    request_helper.main(main_url,"files/jinku_products.json")

    logger.info(f"Completed Scraping...")

    # for code in range(ord('a'), ord('a') + 1):
    #     logger.info(f"Getting Data for code - {chr(code)}")
    #     main_url=f"{JINKU_PRODUCT_URL}?product_id={chr(code)}"
    #     request_helper.main(main_url,"files/jinku_products.json")
    #     logger.info(f"Completed Scraping...")