from common.custom_logger import get_logger
from worldTraders.request_helper import RequestHelper
from worldTraders.constants import IPC_NET_SEARCH_URL, IPC_NET_GET_DETAILS_URL

logger, listener = get_logger("WorldTradersScraper")
listener.start()



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
