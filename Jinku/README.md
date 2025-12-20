# Jinku (Jikiu) Auto Parts Scraper

This directory contains a set of scripts to scrape auto part information from the [Jikiu catalog](https://www.jikiu.com/catalogue). The scraper can be run from the main Streamlit application or as a standalone script for large-scale data collection.

## How to Run

There are two ways to run the scraper.

### 1. Run via the Streamlit App (Recommended)

This is the easiest way to run the scraper for a single product ID and view the results directly in your browser without saving any files.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "Jinku" from the dropdown menu and enter a product ID.

### 2. Run as a Standalone Script

This method is useful for large-scale scraping and saves the output directly to the database and log files.

1.  **Scrape Vehicle Models (One-time setup)**: Run the `helpers.py` script to populate your database with all the vehicle models.
    ```bash
    python Jinku/helpers.py
    ```
2.  **Scrape Product Details**: Edit the `LETTER` variable in `Jinku/main.py` and then run the script.
    ```bash
    python Jinku/main.py
    ```

## Features

-   **Interactive UI**: Can be run from the project's central Streamlit application for ease of use.
-   **Two-Stage Scraping**:
    1.  **Model Scraper**: A separate script (`helpers.py`) crawls all vehicle models for every brand.
    2.  **Product Scraper**: The main script fetches detailed information for individual products based on an ID.
-   **Database Integration**: The standalone script stores all scraped data directly into a MongoDB database.
-   **Concurrent Scraping**: Uses a `ThreadPoolExecutor` to process multiple product URLs concurrently for high performance.
-   **Error Handling**: Manages request retries and logs PDF and errored URLs into separate JSON files for review when run as a standalone script.

## Files

-   `main.py`: The main script for scraping **product** details.
-   `helpers.py`: A script dedicated to crawling and storing vehicle **models** by brand.
-   `request_helper/__init__.py`: The core logic for fetching and parsing product pages.
-   `constants.py`: Contains essential configuration like base URLs, API endpoints, headers, and a list of all vehicle brands.

## Prerequisites

-   A running MongoDB instance (required for standalone script).
-   Correct MongoDB connection details configured within the project's common database files.
-   All required Python packages from the root `requirements.txt` file. Key dependencies include:
    -   `requests`
    -   `beautifulsoup4`
    -   `pymongo`
    -   `psutil`

## Output

-   **Streamlit App**: Displays the scraped data in a clean, interactive table.
-   **Standalone Script**: 
    -   **MongoDB Collections**: Populates `jinku_models_collection` and `jinku_products_collection`.
    -   **JSON Files**: Creates `_pdf.json` and `_errored.json` files in the `files/Jinku/` directory for any skipped or failed URLs.
