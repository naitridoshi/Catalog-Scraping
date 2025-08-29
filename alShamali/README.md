# AlShamali Scraper

An asynchronous web scraper for the [AlShamali online catalog](https://alshamali.online) that extracts product data for various categories.

## How to Run

### 1. Run via the Streamlit App (Recommended)

This provides the best user experience with interactive controls and previews.

1.  Navigate to the project root directory.
2.  Run the command: `streamlit run app.py`
3.  Select "AlShamali" from the dropdown menu and choose your desired brands and output options.

### 2. Run as a Standalone Script

This method processes all categories listed in `items.json` and saves the output to JSON, CSV, and a combined Excel file.

```bash
python alShamali/main.py
```

## Features

-   **Interactive UI**: Run from a central Streamlit application, allowing you to select multiple brands and view results directly in the app.
-   **Asynchronous Processing**: Uses `asyncio` and `httpx` to concurrently scrape multiple product categories for high performance.
-   **Advanced Output Options**: When run from the UI, you can choose to:
    -   Combine all results into a single table.
    -   View a summary table and inspect the data for each brand in a separate, expandable section.
    -   Download all results as a single ZIP file containing individual CSVs for each brand.
-   **Conditional File Saving**: The scraper only saves files to disk when run as a standalone script. No files are saved when run from the Streamlit app.
-   **Multi-Format Output (Standalone)**: Saves scraped data into individual JSON and CSV files for each category, and then compiles everything into a single Excel workbook.

## Files

-   `main.py`: The main entry point to run the scraper.
-   `request_helper/__init__.py`: Contains the core scraping and parsing logic.
-   `items.json`: A list of all product categories to be scraped.

## Prerequisites

Ensure you have the required Python packages installed from the main `requirements.txt` file.

## Output

-   **Streamlit App**: Displays data in a single table or an advanced summary view, with options to download a CSV or a ZIP file.
-   **Standalone Script**: Generates JSON, CSV, and a combined Excel file in the `files/alShamali/` directory.