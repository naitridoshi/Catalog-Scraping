from common.custom_logger import get_logger
from dljParts.request_helper import DLJRequestHelper
from dljParts.constants import DLJ_SEARCH_URL

logger, listener = get_logger("DLJScraper")
listener.start()



if __name__ == '__main__':
    request_helper = DLJRequestHelper()

    SEARCH_QUERY="SUZUKI"  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE

    logger.info(f"Getting Data for query - {SEARCH_QUERY}")
    SEARCH_QUERY=SEARCH_QUERY.replace(" ","+")
    main_url = f"{DLJ_SEARCH_URL}?search={SEARCH_QUERY}"
    try:
        request_helper.main(main_url,f"files/dljParts/{SEARCH_QUERY}.xlsx")
        logger.info(f"Completed Scraping for code - {SEARCH_QUERY} .... ")
    except Exception as e:
        logger.error(f"Empty data found for query - {SEARCH_QUERY} - {str(e)}")
