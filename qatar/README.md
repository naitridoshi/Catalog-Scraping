# Qatar CID Business Directory Scraper

This script is a web scraper designed to extract business listing information from the [Qatar CID](https://qatarcid.com/) directory. It operates on a page-by-page basis, fetching all listings from a specified page number and saving them to a JSON file.

## Features

-   **Dynamic Token Handling**: Automatically fetches a required security token from the website's homepage to make valid API requests.
-   **AJAX Request Handling**: Interacts with the website's internal AJAX endpoint to retrieve the list of businesses for a given page.
-   **Session Management**: Uses a `requests.Session` object to persist cookies and headers across multiple requests.
-   **Page-Based Scraping**: Allows users to target and scrape a specific page of the directory by changing a single variable.

## Files

-   `main.py`: The main entry point to run the scraper. You must edit the `PAGE_NUM` variable in this file to select a page to scrape.
-   `request_helper/__init__.py`: Contains the core logic for fetching the security token, making AJAX requests, and parsing the business details from individual company pages.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file. The key dependencies for this scraper are:
-   `requests`
-   `beautifulsoup4`

## How to Run

1.  **Set the Page Number**: Open `qatar/main.py` and modify the `PAGE_NUM` variable to the desired page number you wish to scrape.

    ```python
    # in qatar/main.py
    PAGE_NUM=1  # ONLY CHANGE THIS. DO NOT CHANGE ANYTHING ELSE PLEASE
    ```

2.  **Run the Scraper**: Execute the script from the project's root directory.

    ```bash
    python qatar/main.py
    ```

## Output

The scraper generates one JSON file per page number inside the `files/qatar/` directory.

-   **`files/qatar/{PAGE_NUM}.json`**: A JSON file containing a list of all businesses found on the specified page. Each business is an object containing its scraped details, such as Phone, Fax, P.O. Box, Email, and Website.
