from common.constants import BASIC_HEADERS
from common.custom_logger import get_logger
from qatar.request_helper import QatarRequestHelper

logger, listener = get_logger("QatarScraper")
listener.start()



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
