from common.custom_logger import get_logger
from dljParts.request_helper import DLJRequestHelper
from dljParts.constants import DLJ_SEARCH_URL
import pandas as pd
import os

logger, listener = get_logger("DLJScraper")
listener.start()


def  run_dljparts_scraper(search_query: str) -> pd.DataFrame:
    """
    Runs the DLJ Parts scraper for a given search query.

    Args:
        search_query: The part name or query to search for.

    Returns:
        A pandas DataFrame containing the scraped data, or an empty DataFrame if no data is found.
    """
    request_helper = DLJRequestHelper()

    logger.info(f"Getting Data for query - {search_query}")
    query_param = search_query.replace(" ", "+")
    main_url = f"{DLJ_SEARCH_URL}?search={query_param}"

    try:
        # Call the helper to return a DataFrame directly, without saving any files.
        df = request_helper.main(main_url, return_df=True)
        logger.info(f"Completed Scraping for code - {search_query} .... ")
        return df

    except Exception as e:
        logger.error(f"An error occurred while scraping for query - {search_query} - {str(e)}")
        return pd.DataFrame()


if __name__ == '__main__':
    SEARCH_QUERY = "SUZUKI"  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE
    
    logger.info(f"Running DLJ Scraper as a standalone script for query: {SEARCH_QUERY}")
    request_helper = DLJRequestHelper()
    query_param = SEARCH_QUERY.replace(" ", "+")
    main_url = f"{DLJ_SEARCH_URL}?search={query_param}"
    
    output_dir = "files/dljParts"
    os.makedirs(output_dir, exist_ok=True)
    output_filename = f"{output_dir}/{query_param}.xlsx"
    
    # Call main with a filename to save the file to disk.
    request_helper.main(main_url, filename=output_filename)
    logger.info(f"Scraping complete. File saved to {output_filename}")
