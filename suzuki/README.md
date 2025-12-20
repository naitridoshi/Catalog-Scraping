# Maruti Suzuki Parts Catalog Scraper

This directory contains a set of scripts to scrape genuine parts data from the official [Maruti Suzuki](https://www.marutisuzuki.com/genuine-parts) website. It can be run via the main Streamlit application or as a series of standalone scripts.

## How to Run

### 1. Run via the Streamlit App (Recommended)

This provides the best user experience with interactive controls and previews.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "Suzuki" from the dropdown menu and choose your desired models and output options.

### 2. Run as a Standalone Script

This method is for large-scale data collection and saves the output to JSON files.

1.  Run the `main.py` script to fetch all the parts data from the API. This will create a series of JSON files in the `files/suzuki/` directory, one for each car model.
    ```bash
    python suzuki/main.py
    ```
2.  Optionally, you can then use the `convert_to_csv.py` and `store_to_db.py` scripts to process these files.

## Features

-   **Interactive UI**: Run from a central Streamlit application, allowing you to select multiple models and view results directly in the app.
-   **API-Driven**: Interacts directly with the website's backend API to ensure fast and reliable data retrieval.
-   **Concurrent Scraping**: Fetches pages for each model concurrently using multithreading to improve performance.
-   **Advanced Output Options**: When run from the UI, you can choose to:
    -   Combine all results into a single table.
    -   View a summary table and inspect the data for each model in a separate, expandable section.
    -   Download all results as a single ZIP file containing individual CSVs for each model.
-   **Conditional File Saving**: The scraper only saves files to disk when run as a standalone script.

## Files

-   `main.py`: The main script for scraping the parts data.
-   `request_helper/__init__.py`: Contains the core logic for making POST requests to the Suzuki API.
-   `constants.py`: Defines the list of all car `MODELS` to be scraped and the required HTTP headers.
-   `convert_to_csv.py`: A standalone utility to convert the scraped JSON files into CSV format.
-   `store_to_db.py`: A standalone utility to load the data from the JSON files into a MongoDB database.

## Prerequisites

-   `requests`, `pandas`, `pymongo`

## Output

-   **Streamlit App**: Displays data in a single table or an advanced summary view, with options to download a CSV or a ZIP file.
-   **Standalone Script**: Creates one JSON file per model in the `files/suzuki/` directory.