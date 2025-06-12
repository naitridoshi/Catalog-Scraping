import time
from json import JSONDecodeError
from typing import List
from googlesearch import search
from json import loads

from common.custom_logger import get_logger, color_string
from insta_cafe.constants import GOOGLE_GEMINI_EMAIL_PROMPT
from insta_cafe.helpers import extract_structured_data_from_html
from insta_cafe.request_helper import InstaCafeRequestHelper
import google.generativeai as genai

logger, listener= get_logger("insta_cafe_searcher")
listener.start()

NAITRI_GOOGLE_GEMINI_API_KEY = 'AIzaSyBzcqyoEjblRFEF0ioqsiTclvy2lm7JNdY'
GOOGLE_GEMINI_MODEL = 'models/gemini-2.0-flash'

genai.configure(api_key=NAITRI_GOOGLE_GEMINI_API_KEY)
model = genai.GenerativeModel(model_name=GOOGLE_GEMINI_MODEL)

def get_gemini_response(
    html_content: str = None,
    clean_text: bool = True,
    contents: list = None,
    prompt: str = 'Always answer the question to the point!!'
):
    """
    Generates a response from the Gemini model.

    :param html_content: HTML content to pass to the Gemini model.
    :param contents: List of contents to pass to the Gemini model
        it can be a list of prompts, images, text, etc.
    :param clean_text: Whether to clean the text or not.
    :param prompt: Prompt to pass to the Gemini model.

    :return: Response from Gemini model.
    """
    if contents is None:
        contents = list()
    try:
        start_time = time.time()
        if clean_text and html_content:
            html_content = extract_structured_data_from_html(html_content)
            contents.append(html_content)

        if len(contents) == 0:
            logger.warning("No contents to pass to the Gemini model!!")
            raise Exception("No contents to pass to the Gemini model!!")

        # Generate content
        response = model.generate_content(
            contents=[
                prompt,
                *contents
            ]
        )
        total_token_count = response.usage_metadata.total_token_count

        logger.debug(
            f"Time taken to get response from Gemini: "
            f"{color_string(f'{(time.time() - start_time):.2f} seconds.')}"
        )
        logger.debug(
            {
                "totalTokenCount": total_token_count,
                "promptTokenCount": response.usage_metadata.prompt_token_count,
                "responseTokenCount":
                    response.usage_metadata.candidates_token_count,
                "cachedTokenCount":
                    response.usage_metadata.cached_content_token_count
            }
        )
        return response.text, total_token_count

    except JSONDecodeError:
        logger.error(f"Error decoding JSON.")
        raise Exception(f"Failed to decode gemini response.")
    except Exception as e:
        logger.error(f"Error generating content using gemini: {e}")
        raise Exception(f"Error generating content using gemini: {e}.")


def get_links_from_google_search(
    query: str,
    num_results: int = 10
) -> List[str] | None:
    """
    Fetches Google search results for a given query.

    Args:
        query (str): The search query.
        num_results (int): The number of results to return.

    Returns:
        List[str]: A list of strings containing the search result links.
    """
    links = []
    try:
        response = search(term=query, num_results=num_results)
        for link in response:
            if link.startswith("http"):
                links.append(link)
    except Exception as e:
        logger.error(f"An error occurred while fetching search results: {e}")
    if len(links) == 0:
        logger.error(f"No links found for the query: {query}")
        return None
    logger.debug(f"{len(links)} links found for the query: {query}")
    return links

def get_page_information(url: str, request_helper:InstaCafeRequestHelper) -> tuple[dict, int] | None:
    token_used = 0
    page_information = None
    logger.debug(f"Processing: {url}")
    try:
        res = request_helper.request(method="GET", url=url)
        if res is None:
            return None

        page_information, token_used = get_gemini_response(
            html_content=res.text,
            clean_text=True,
            prompt=GOOGLE_GEMINI_EMAIL_PROMPT
        )
    except Exception as e:
        logger.error(f"Error getting information from {url}: {e}")
    return page_information, token_used

