# Insta-Cafe Instagram Username Finder

This script is a data enrichment tool designed to find the Instagram usernames for a list of restaurants. It reads restaurant data from a JSON file, uses Google Search to find the official Instagram page for each restaurant, and then parses the page to extract the Instagram handle.

## Features

-   **Data Enrichment**: Instead of scraping from a single source, this tool enriches an existing dataset with new information (Instagram usernames).
-   **Google Search Integration**: Leverages Google Search to find the most relevant Instagram page for a given restaurant name, increasing the accuracy of the results.
-   **AI-Powered Parsing**: Appears to use a generative AI model (based on the prompt in `constants.py`) to intelligently parse the HTML of a webpage and extract the specific Instagram username, even if the page structure is complex.

## Files

-   `main.py`: The main entry point for the script. It reads the input file, orchestrates the search and extraction process, and saves the final enriched data.
-   `request_helper/__init__.py`: A helper class for making HTTP requests.
-   `helpers.py`: Contains utility functions for extracting text and links from HTML content.
-   `constants.py`: Contains the prompt template used for the AI-powered username extraction.

## Prerequisites

-   An input JSON file named `files/rajkot_data.json`. This file should contain a list of restaurant objects, each with a "Name" key.
-   An implementation for `get_links_from_google_search` and `get_page_information`, which likely rely on external APIs for Google Search and a generative AI model.
-   Required Python packages from the root `requirements.txt` file, including:
    -   `requests`
    -   `beautifulsoup4`

## How to Run

1.  **Prepare the Input File**: Ensure you have a valid `files/rajkot_data.json` file in place with the list of restaurants you want to process.

2.  **Run the Script**: Execute the `main.py` script from the project's root directory.

    ```bash
    python insta_cafe/main.py
    ```

## Output

The script will generate a single new JSON file in the `files/` directory.

-   **`files/complete_new.json`**: This file contains a JSON array of all the original restaurant objects, with a new `"username"` field added to each one containing the discovered Instagram handle.
