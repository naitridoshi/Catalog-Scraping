import json

from common.custom_logger import get_logger
from insta_cafe import get_links_from_google_search, get_page_information, InstaCafeRequestHelper

logger, listener= get_logger("insta_cafe_main")
listener.start()


def main(query, request_helper):
    logger.info("Starting Google Search")
    all_info=[]
    links=get_links_from_google_search(query, num_results=40)
    logger.info(f"Received {len(links)} to search ....")
    for link in links:
        page_information, token_usage=get_page_information(link, request_helper)
        if page_information is None:
            logger.warning("No Page Info FOund!!!")
            continue
        logger.debug(f"Page Information Found is : {page_information}")
        all_info.append(page_information)

    logger.info("COmplete scraped now saving to file")
    with open("files/cafe.json","w") as f:
        json.dump(all_info, f, indent=4)
    logger.info("DONE")

if __name__ == '__main__':
    request_helper=InstaCafeRequestHelper()
    QUERY="Cafes in Rajkot Instagram"
    main(QUERY,request_helper)