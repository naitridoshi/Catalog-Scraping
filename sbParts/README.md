# SB-PARTS Japan Scraper

This directory contains a powerful, two-stage asynchronous scraper for the [SB-PARTS Japan](https://sbparts.jp/) auto parts catalog. It can be run from the main Streamlit application to fetch individual part data or as a standalone script to collect all parts.

## How to Run

### 1. Run via the Streamlit App (Recommended)

This is the easiest way to get data for a specific part number.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "SB Parts" from the dropdown menu and enter a part number.

### 2. Run as a Standalone Script

This method is for large-scale data collection and saves data directly to MongoDB.

1.  **Prerequisite**: Ensure you have an input JSON file named `autoSparePartsCatalog.sbparts_parts_data.json` in the `sbParts/` directory. This file must contain a list of products, with each product having a `pid`, `part_no`, and `p_brand`.
2.  **Run the scraper**:
    ```bash
    python sbParts/main.py
    ```

## Features

-   **Interactive UI**: The Streamlit app provides an interface for scraping individual part numbers.
-   **Two-Stage Scraping Process**:
    1.  **API-Based Part Collector**: An asynchronous function (`collect_all_part_numbers`) can be used to systematically query an API endpoint to discover all available part numbers.
    2.  **Web-Based Detail Scraper**: The main script reads a list of parts from a JSON file, visits the individual catalog page for each part, and scrapes detailed information.
-   **Asynchronous Architecture**: Uses `httpx` and `asyncio` for high-concurrency requests.
-   **Direct to Database (Standalone)**: All collected data is saved directly into a MongoDB collection when run as a standalone script.

## Files

-   `main.py`: The main entry point for the scraper.
-   `request_helper/__init__.py`: Contains the core logic for both the API collector and the web scraper.
-   `constants.py`: Defines the API endpoints and headers.
-   `db.py`: Contains the database writer logic for saving data to MongoDB.

## Prerequisites

-   A running MongoDB instance with the connection configured (for standalone mode).
-   All required Python packages from the root `requirements.txt` file.

## Output

-   **Streamlit App**: Displays detailed data for the requested part number in an interactive table.
-   **Standalone Script**: Populates a MongoDB collection with highly detailed documents.