# Catalog Scraping Project

## Overview

This project is a collection of web scrapers designed to extract data from various auto parts and business directory websites. The entire suite of scrapers is unified under a single, easy-to-use web interface built with Streamlit, allowing for simple operation without needing to edit code for most tasks.

Each scraper is organized into its own directory and can be run either from the central Streamlit application or as a standalone Python script for more advanced, large-scale data collection.

## Features

-   **Centralized Web UI**: An interactive Streamlit application (`app.py`) serves as the main entry point to run all scrapers.
-   **Modular Scraper Architecture**: Each scraper is self-contained in its own directory.
-   **Advanced Scraping Capabilities**: Utilizes modern Python libraries like `httpx`, `asyncio`, and `multithreading` for high-performance, concurrent scraping.
-   **Flexible Output Options**: The Streamlit UI provides options to view data directly, combine results from multiple categories, and download data as CSV or ZIP files.
-   **Conditional File I/O**: Scrapers run from the Streamlit app process and display data in memory without cluttering the file system. When run as standalone scripts, they save their output to structured files (JSON, CSV, Excel).

## Setup and Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repository-url>
    ```

2.  **Navigate to the project directory**:
    ```bash
    cd Catalog-Scraping
    ```

3.  **Install dependencies**:
    It is recommended to use a virtual environment. Once your environment is activated, install all required packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Main Application

To launch the web interface, run the `app.py` file with Streamlit from the project's root directory.

```bash
streamlit run app.py
```

This will open a new tab in your default web browser with the application running. From there, you can select any scraper from the dropdown menu and provide the necessary inputs.

## Available Scrapers

The project includes the following scrapers. For more detailed information on each, please refer to the `README.md` file within the respective directory.

-   **AlShamali**: Scrapes product data by brand from an online auto parts catalog.
-   **DLJ Parts**: Fetches auto parts based on a search query.
-   **Jinku (Jikiu)**: A two-stage scraper to first collect vehicle models and then scrape detailed product information by ID.
-   **Mr. Media**: Scrapes a business directory by category.
-   **OCR**: A utility to extract text and images from documents.
-   **SB Parts**: Scrapes detailed auto part data from the SB-PARTS Japan catalog.
-   **Supreme Motors**: Scrapes product data from the Supreme Motor Parts website.
-   **Suzuki**: Fetches genuine parts data for various Maruti Suzuki car models from a backend API.
-   **World Traders**: Scrapes company contact information from the IPCNet Exporters Directory.
