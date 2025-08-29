# Supreme Motor Parts Scraper

This is an asynchronous web scraper for the [Supreme Motor Parts](https://www.suprememotorparts.com/) website. It is designed to discover all product pages, scrape detailed information from each, and compile the results into a single CSV file.

## Features

-   **Asynchronous Scraping**: Uses `asyncio` and `httpx` to process up to 10 product pages concurrently, ensuring efficient and fast data collection.
-   **Comprehensive Data Extraction**: Scrapes a wide variety of product details, including name, image URL, specifications (e.g., Application, Size), and business terms (e.g., Minimum Order Quantity, Price).
-   **Row-by-Row CSV Writing**: Streams scraped data directly to a CSV file one row at a time, which is highly memory-efficient.
-   **Dual-Format Output**: Saves all collected data into a single, timestamped CSV file for easy use in spreadsheets, and also creates a full JSON dump as a backup.

## Files

-   `main.py`: The main entry point to execute the scraper.
-   `request_helper/__init__.py`: Contains all the core logic for discovering URLs, parsing product pages, and writing data to the output files.
-   `constants.py`: Defines the starting URL for the scraper.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file. The key dependencies for this scraper are:
-   `httpx`
-   `asyncio`
-   `beautifulsoup4`
-   `requests`

## How to Run

The scraper can be run directly from the project's root directory without any configuration.

```bash
python supreme_motors/main.py
```

## Output

The scraper generates files in two locations:

-   **CSV File**: A single, timestamped CSV file containing all scraped products will be created in the `files/supreme_motors/` directory.
    -   `files/supreme_motors/supreme_motors_products_{TIMESTAMP}.csv`
-   **JSON File**: A file named `data2.json` will be created in the project's root directory, containing a JSON array of all the scraped product data.
