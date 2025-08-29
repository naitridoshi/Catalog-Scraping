# World Traders (IPCNet) Directory Scraper

This script is a web scraper for the [IPCNet Exporters Directory](https://www.ipcnet.org/exporters/). It is designed to iterate through all the pages of the directory, extract the contact information for each company listed, and save the results into a single Excel file.

## Features

-   **Multi-Page Scraping**: Automatically iterates through all 48 pages of the directory to ensure a complete data set.
-   **Detailed Data Extraction**: Parses key information for each company, including Company Name, Contact Person, Email, Phone Number, Last Updated date, and Seen By count.
-   **Intelligent Excel Appending**: All data is saved to a single Excel file. The script is smart enough to append new data to the existing file and will even create new sheets if the current one exceeds a row limit, preventing overly large files.
-   **Formatted Output**: The resulting Excel file is well-formatted with custom headers, colors, and auto-adjusted column widths for excellent readability.

## Files

-   `main.py`: The main entry point to run the scraper. It contains the loop that goes through all the directory pages.
-   `request_helper/__init__.py`: Contains the core logic for fetching pages, parsing the company listings, and saving the data to the Excel file.
-   `constants.py`: Defines the base URLs for the scraper.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file. The key dependencies for this scraper are:
-   `requests`
-   `beautifulsoup4`
-   `pandas`
-   `openpyxl`

## How to Run

The scraper can be run directly from the project's root directory without any configuration. It is pre-configured to scrape all pages from 1 to 48.

```bash
python worldTraders/main.py
```

## Output

The scraper generates a single Excel file in the `files/ipcNet/` directory.

-   **`files/ipcNet/importers_and_exporters.xlsx`**: A single Excel workbook containing all the scraped company data from every page of the directory. If the number of rows is very large, the data will be split across multiple sheets within this one file.
