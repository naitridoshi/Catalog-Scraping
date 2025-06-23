#!/usr/bin/env python3
"""
Script to convert JSON files from files/suzuki directory to CSV format
and save them in the suzuki directory.
"""

import json
import csv
import os
import glob
from pathlib import Path


def convert_json_to_csv(json_file_path, csv_file_path):
    """
    Convert a single JSON file to CSV format.
    
    Args:
        json_file_path (str): Path to the input JSON file
        csv_file_path (str): Path to the output CSV file
    """
    try:
        # Read JSON data
        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        
        if not data:
            print(f"Warning: {json_file_path} is empty or contains no data")
            return
        
        # Get fieldnames from the first record
        fieldnames = list(data[0].keys())
        
        # Write to CSV
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for record in data:
                writer.writerow(record)
        
        print(f"✓ Converted: {os.path.basename(json_file_path)} -> {os.path.basename(csv_file_path)}")
        
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing JSON in {json_file_path}: {e}")
    except Exception as e:
        print(f"✗ Error converting {json_file_path}: {e}")


def main():
    """
    Main function to process all JSON files in files/suzuki directory.
    """
    # Define paths
    source_dir = Path("files/suzuki")
    output_dir = Path("suzuki")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Get all JSON files in the source directory
    json_files = list(source_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {source_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to convert...")
    print("-" * 50)
    
    # Convert each JSON file to CSV
    for json_file in json_files:
        # Create CSV filename by replacing .json extension with .csv
        csv_filename = json_file.stem + ".csv"
        csv_file_path = output_dir / csv_filename
        
        convert_json_to_csv(json_file, csv_file_path)
    
    print("-" * 50)
    print(f"Conversion completed! CSV files saved in {output_dir}")


if __name__ == "__main__":
    main()
