# AlShamali Scraper

An asynchronous web scraper for AlShamali online catalog that extracts product data and saves it in multiple formats.

## Features

- **Asynchronous Processing**: Uses `asyncio` for concurrent scraping of multiple categories
- **Multiple Output Formats**: Saves data to JSON, CSV, and Excel formats
- **Controlled Concurrency**: Limits concurrent requests to avoid overwhelming the server
- **Error Handling**: Robust error handling with detailed logging
- **Combined Excel Workbook**: Creates a single Excel file with all categories as separate sheets

## Files

- `main.py`: Main asynchronous scraper script
- `test_async.py`: Test script for verifying functionality
- `request_helper/__init__.py`: Core scraping logic
- `constants.py`: Configuration constants
- `items.json`: List of categories to scrape

## Usage

### Run the full scraper
```bash
python alShamali/main.py
```

### Test with a subset of items
```bash
python alShamali/test_async.py
```

## Output

The scraper generates the following files in the `files/alShamali/` directory:

### Individual Files
- `{Category_Name}_data.json`: JSON file for each category
- `{Category_Name}_data.csv`: CSV file for each category

### Combined Excel Workbook
- `alShamali_combined_data.xlsx`: Single Excel file containing:
  - **Summary Sheet**: Overview of all categories with item counts and status
  - **Individual Sheets**: One sheet per category with all product data

## Configuration

### Concurrency Settings
- `max_concurrent_requests`: Number of concurrent page requests (default: 5)
- `max_concurrent`: Number of concurrent categories to process (default: 3)

### Delays (Anti-Blocking Strategy)
- **Initial delay**: 5-10 seconds before starting scraping
- **Item delays**: 2-5 seconds before processing each category
- **Page delays**: 2-5 seconds between page requests
- **Batch delays**: 5-10 seconds between page batches
- **Category delays**: 8-15 seconds between category groups
- **Retry delays**: Progressive delays (3s, 6s, 9s) for failed requests
- **Test delays**: 3-7 seconds between test items

## Data Structure

Each scraped product includes:
- All original product fields from the website
- `Category`: The category name
- `Category_Image`: The category image URL
- `Source_URL`: The source URL for the category

## Error Handling

- Automatic retries for failed requests (up to 4 attempts)
- Graceful handling of missing data
- Detailed logging of all operations
- Summary report of successful vs failed categories

## Dependencies

- `asyncio`: For asynchronous processing
- `httpx`: For HTTP requests
- `pandas`: For Excel workbook creation
- `openpyxl`: For Excel file writing
- `beautifulsoup4`: For HTML parsing
- `requests`: For HTTP requests (fallback)

## Performance

- Processes multiple categories concurrently
- Batches page requests within each category
- Uses shared HTTP clients for better performance
- Implements rate limiting to respect server resources

## Anti-Blocking Strategy

The scraper implements multiple layers of delays to prevent cookie-based blocking:

1. **Initial Delay**: Waits 5-10 seconds before making any requests
2. **Category Delays**: Waits 2-5 seconds before processing each category
3. **Page Delays**: Waits 2-5 seconds between individual page requests
4. **Batch Delays**: Waits 5-10 seconds between page batches within a category
5. **Group Delays**: Waits 8-15 seconds between category groups
6. **Retry Delays**: Uses progressive delays (3s, 6s, 9s) for failed requests

All delays are randomized to avoid predictable patterns that could trigger blocking mechanisms.

## Logging

The scraper provides detailed logging including:
- Progress updates for batches and individual items
- Error messages with context
- Performance metrics (time taken, items processed)
- Summary statistics at completion 