# DLJ Auto Parts Scraper

A web scraper for [DLJ Auto Parts](https://www.dlj-autoparts.com) that searches for products based on a query.

## How to Run

### 1. Run via the Streamlit App (Recommended)

This is the easiest way to run the scraper and view the results directly in your browser.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "DLJ Parts" from the dropdown menu and enter a search query.

### 2. Run as a Standalone Script

This method saves the output directly to a formatted Excel file.

1.  **Edit the search query**: Open the `dljParts/main.py` file and modify the `SEARCH_QUERY` variable.
2.  **Run the script**: Execute the main script from the project's root directory.
    ```bash
    python dljParts/main.py
    ```

## Features

-   **Interactive UI**: Can be run from the project's central Streamlit application.
-   **Search-Based Scraping**: Fetches data by executing a search query on the website.
-   **Detailed Product Data**: Parses OEM numbers, car name, product details, and more.
-   **Conditional File Saving**: Only saves an Excel file when run as a standalone script. The Streamlit app displays the data directly.
-   **Formatted Excel Output (Standalone)**: Saves data into a well-structured and "prettified" Excel file with custom headers, colors, and auto-adjusted column widths.

## Files

-   `main.py`: The main script to run the scraper.
-   `request_helper/__init__.py`: Contains the core scraping, parsing, and Excel generation logic.
-   `constants.py`: Defines the base search URL.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file.

## Output

-   **Streamlit App**: Displays the scraped data in an interactive table.
-   **Standalone Script**: Generates a single, formatted Excel file in the `files/dljParts/` directory.