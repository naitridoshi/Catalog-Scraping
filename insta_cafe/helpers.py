import re

from bs4 import BeautifulSoup, NavigableString, Tag


def extract_links_from_html(html_content: str, soup=None) -> list:
    """
    Extracts three sets of data using three separate regexes:
      1. Links from anchor tags (href attribute) using BeautifulSoup.
      2. Actual URLs from anchor tags (href attribute) using regex.
      3. 'https' plus up to 50 characters.
      4. 'href' plus up to 70 characters.

    Returns a list of all matches found.
    """
    if soup is None:
        soup = BeautifulSoup(html_content, 'html.parser')

    href_links = soup.find_all('a', href=True)
    href_links = [link['href'] for link in href_links]

    pattern_a_href = re.compile(
        r'<a\b[^>]*?\bhref\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE
    )

    pattern_https_snippet = re.compile(r'https{0,50}', re.IGNORECASE)

    pattern_href_snippet = re.compile(r'href{0,70}', re.IGNORECASE)

    links_from_a_tags = pattern_a_href.findall(html_content)
    snippets_with_https = pattern_https_snippet.findall(html_content)
    snippets_with_href = pattern_href_snippet.findall(html_content)

    all_results = set(
        href_links +
        links_from_a_tags +
        snippets_with_https +
        snippets_with_href
    )

    return list(all_results)


def extract_text_content_from_html(html_content: str):
    """
    Extracts structured content from HTML, organizing text under headings.

    :param html_content: HTML content to parse.
    :return: A list of dictionaries, each containing a heading and its
    associated text.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    structured_content = []
    current_heading = None
    current_text = []

    for element in soup.recursiveChildGenerator():
        if (
                isinstance(element, Tag) and
                element.name and
                element.name.startswith('h') and
                element.name[1:].isdigit()
        ):
            # Save the current heading and its text
            if current_heading:
                structured_content.append(
                    {
                        "heading": current_heading,
                        "text": ' '.join(current_text).strip()
                    }
                )
            # Start a new heading
            current_heading = element.get_text(strip=True)
            current_text = []
        elif isinstance(element, NavigableString) and current_heading:
            # Collect text under the current heading
            cleaned_text = re.sub(r'\s+', ' ', element).strip()
            current_text.append(cleaned_text)

    # Add the last heading and its text
    if current_heading:
        structured_content.append(
            {
                "heading": current_heading,
                "text": ' '.join(current_text).strip()
            }
        )

    return str(re.sub(r'\s+', ' ', str(structured_content)).strip())


def extract_structured_data_from_html(html_content: str):
    """
    Extracts text and links from HTML content using BeautifulSoup and regex.

    :param html_content: HTML content to parse.
    :return: A dictionary containing plain text and links extracted from the
    HTML.
    """
    return str(
        {
            "textContent": extract_text_content_from_html(html_content),
            "links": extract_links_from_html(html_content)
        }
    )


def extract_data_from_html(html_content: str):
    """
    Extracts text and links from HTML content using BeautifulSoup and regex.

    :param html_content: HTML content to parse.
    :return: A dictionary containing plain text and links extracted from the
    HTML.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text()

    return str(
        {
            "textContent": text_content,
            "links": extract_links_from_html(html_content)
        }
    )
