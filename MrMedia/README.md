# Mr. Media Business Directory Scraper

This script is an asynchronous web scraper for the [Mr. Media Business Directory](https://directory.mymrmedia.com/). It is designed to crawl business categories, extract the details of each listing, and display the results.

## How to Run

### Run via the Streamlit App (Recommended)

This provides the best user experience with interactive controls and previews.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "Mr. Media" from the dropdown menu and choose your desired categories and output options.

### Run as a Standalone Script

The standalone script is used to generate the `mr_media_categories.json` file, which is used by the Streamlit app.

```bash
python MrMedia/main.py
```

## Features

-   **Interactive UI**: Run from a central Streamlit application, allowing you to select multiple categories and view results directly in the app.
-   **Asynchronous Scraping**: Uses `asyncio` and `httpx` to concurrently process multiple category pages for faster data collection.
-   **Advanced Output Options**: When run from the UI, you can choose to:
    -   Combine all results into a single table.
    -   View a summary table and inspect the data for each category in an expandable section.
    -   Download all results as a single ZIP file containing individual CSVs for each category.
-   **Conditional File Saving**: The scraper only saves files to disk when the standalone script is run to generate categories. No files are saved when run from the Streamlit app.
-   **Robust Parsing**: Capable of handling multiple page layouts found on the site.

## Files

-   `main.py`: The main entry point for the scraper. Can be run from the Streamlit app or as a standalone script to generate the category list.
-   `request_helper/__init__.py`: Contains all the core logic for fetching categories, scraping listings, and preparing data.
-   `constants.py`: Stores the required HTTP headers and base URL.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file.

## Output

-   **Streamlit App**: Displays data in a single table or an advanced summary view, with options to download a CSV or a ZIP file.
-   **Standalone Script**: Generates `mr_media_categories.json` in the project root.