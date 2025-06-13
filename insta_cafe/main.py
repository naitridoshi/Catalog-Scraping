import json

from common.custom_logger import get_logger
from insta_cafe import get_links_from_google_search, get_page_information, InstaCafeRequestHelper

logger, listener= get_logger("insta_cafe_main")
listener.start()


def main(query, request_helper):
    logger.info("Starting Google Search")
    # all_info=[]
    link=get_links_from_google_search(query, num_results=1)
    logger.debug(f"LINK - {link}")
    link=link[0]
    logger.info(f"Received {link} to search ....")
    page_information, token_usage=get_page_information(link, request_helper)
    if page_information is None:
        logger.warning("No Page Info FOund!!!")
        return
    logger.debug(f"Page Information Found is : {page_information}")
    return page_information

        # all_info.append(page_information)

    # logger.info("COmplete scraped now saving to file")
    # with open("files/cafe.json","w") as f:
    #     json.dump(all_info, f, indent=4)
    # logger.info("DONE")

if __name__ == '__main__':
    request_helper=InstaCafeRequestHelper()

    with open("files/rajkot_data.json","r") as f:
        complete_data=json.load(f)

    new_docs=[]
    for complete_doc in complete_data:
        doc=complete_data[complete_doc]
        logger.info(f"DICTT: {doc}")
        restaurant_name=doc.get("Name")
        QUERY=restaurant_name + "Instagram"
        logger.info(f"EXECUTING {QUERY}")
        username=main(QUERY,request_helper)
        logger.debug(f"USERNAME RECEIVED = {username}")
        doc["username"]=username
        new_docs.append(doc)
        logger.info(f"DONE FOR {QUERY}")

    with open("files/complete_new.json", "w") as f:
        json.dump(new_docs, f, indent=2)

    logger.info("SAVEDDDD")