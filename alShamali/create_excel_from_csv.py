import os
import pandas as pd
import re
from datetime import datetime
from common.custom_logger import get_logger

logger, listener = get_logger("ExcelCreator")
listener.start()

def parse_price_data(price_str):
    """
    Parse price data that contains both AED and USD values
    Example: "AED 97.97\n(26.68 $)" -> {"AED": "97.97", "USD": "26.68"}
    """
    if not price_str or pd.isna(price_str):
        return {"AED": "", "USD": ""}
    
    price_str = str(price_str).strip()
    
    # Extract AED value
    aed_match = re.search(r'AED\s*([\d,]+\.?\d*)', price_str)
    aed_value = aed_match.group(1) if aed_match else ""
    
    # Extract USD value
    usd_match = re.search(r'\(([\d,]+\.?\d*)\s*\$\)', price_str)
    usd_value = usd_match.group(1) if usd_match else ""
    
    return {"AED": aed_value, "USD": usd_value}

def process_csv_for_excel(csv_path):
    """
    Process CSV file and split price data into separate columns
    """
    try:
        # Read CSV file
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Ensure we have at least one row and column
        if df.empty:
            logger.warning(f"Empty CSV file: {csv_path}")
            # Create a minimal DataFrame with standard columns
            df = pd.DataFrame({
                'Description': ['No data available'],
                'Price_AED': [''],
                'Price_USD': [''],
                'Price_Original': [''],
                'Category': ['Unknown'],
                'Status': ['Empty file']
            })
            return df
        
        # Check if Price column exists
        if 'Price' in df.columns:
            # Parse price data
            price_data = df['Price'].apply(parse_price_data)
            
            # Create separate columns for AED and USD
            df['Price_AED'] = price_data.apply(lambda x: x['AED'])
            df['Price_USD'] = price_data.apply(lambda x: x['USD'])
            
            # Keep original price column for reference
            df['Price_Original'] = df['Price']
            
            # Remove the original Price column to avoid confusion
            df = df.drop('Price', axis=1)
            
            logger.info(f"Processed price data for {csv_path}: {len(df)} rows")
        else:
            logger.warning(f"No 'Price' column found in {csv_path}, adding empty price columns")
            # Add empty price columns to maintain consistency
            df['Price_AED'] = ''
            df['Price_USD'] = ''
            df['Price_Original'] = ''
        
        # Ensure we have at least one column with data
        if len(df.columns) == 0:
            logger.warning(f"No columns found in {csv_path}, adding default columns")
            df = pd.DataFrame({
                'Description': ['No data available'],
                'Price_AED': [''],
                'Price_USD': [''],
                'Price_Original': [''],
                'Category': ['Unknown'],
                'Status': ['No columns']
            })
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing {csv_path}: {str(e)}")
        # Return a minimal DataFrame instead of None
        return pd.DataFrame({
            'Description': ['Error processing file'],
            'Price_AED': [''],
            'Price_USD': [''],
            'Price_Original': [''],
            'Category': ['Error'],
            'Status': [f'Error: {str(e)}']
        })

def create_excel_from_csv_files(csv_directory="files/alShamali", output_filename="alShamali_combined_data.xlsx"):
    """
    Create Excel workbook from existing CSV files with proper price handling
    """
    try:
        # Create files directory if it doesn't exist
        os.makedirs(csv_directory, exist_ok=True)
        excel_path = f'{csv_directory}/{output_filename}'
        
        # Find all CSV files
        csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]
        
        if not csv_files:
            logger.error(f"No CSV files found in {csv_directory}")
            return None
        
        logger.info(f"Found {len(csv_files)} CSV files to process")
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Create summary data
            summary_data = []
            
            # First pass: collect all summary data
            logger.info("First pass: Collecting summary data...")
            for csv_file in sorted(csv_files):
                csv_path = os.path.join(csv_directory, csv_file)
                category_name = csv_file.replace('_data.csv', '').replace('_', ' ')
                
                logger.info(f"Analyzing {csv_file}...")
                
                # Process the CSV file
                df = process_csv_for_excel(csv_path)
                
                # Always add to summary (df will never be None now)
                if df is not None and not df.empty:
                    # Check if this is a valid data file or an error placeholder
                    if 'Status' in df.columns and df['Status'].iloc[0] in ['Empty file', 'No columns', 'Error processing file']:
                        # This is an error placeholder
                        status = 'Failed'
                        error_msg = df['Status'].iloc[0]
                        total_items = 0
                        price_aed_count = 0
                        price_usd_count = 0
                    else:
                        # This is valid data
                        status = 'Success'
                        error_msg = ''
                        total_items = len(df)
                        price_aed_count = len(df[df['Price_AED'] != '']) if 'Price_AED' in df.columns else 0
                        price_usd_count = len(df[df['Price_USD'] != '']) if 'Price_USD' in df.columns else 0
                else:
                    # Fallback for any unexpected issues
                    status = 'Failed'
                    error_msg = 'Unexpected error'
                    total_items = 0
                    price_aed_count = 0
                    price_usd_count = 0
                
                summary_data.append({
                    'Category': category_name,
                    'Total Items': total_items,
                    'Status': status,
                    'CSV File': csv_file,
                    'Price_AED_Count': price_aed_count,
                    'Price_USD_Count': price_usd_count,
                    'Error': error_msg
                })
                
                if status == 'Success':
                    logger.info(f"✓ Analyzed {csv_file}: {total_items} items")
                else:
                    logger.warning(f"⚠ Analyzed {csv_file}: {error_msg}")
            
            # Create Summary sheet FIRST (this will be the first sheet)
            logger.info("Creating Summary sheet (first sheet)...")
            simple_summary = []
            for result in summary_data:
                simple_summary.append({
                    'Category': result['Category'],
                    'Total Items': result['Total Items'],
                    'Status': result['Status'],
                    'Error': result.get('Error', '')
                })
            
            simple_summary_df = pd.DataFrame(simple_summary)
            simple_summary_df.to_excel(writer, sheet_name='Summary', index=False)
            logger.info(f"✓ Created Summary sheet with {len(simple_summary)} categories")
            
            # Create detailed summary sheet
            logger.info("Creating Detailed_Summary sheet...")
            detailed_summary_df = pd.DataFrame(summary_data)
            detailed_summary_df.to_excel(writer, sheet_name='Detailed_Summary', index=False)
            logger.info(f"✓ Created Detailed_Summary sheet with {len(summary_data)} categories")
            

            
            # Second pass: create individual category sheets
            logger.info("Second pass: Creating individual category sheets...")
            for csv_file in sorted(csv_files):
                csv_path = os.path.join(csv_directory, csv_file)
                category_name = csv_file.replace('_data.csv', '').replace('_', ' ')
                
                logger.info(f"Creating sheet for {csv_file}...")
                
                # Process the CSV file again for the sheet
                df = process_csv_for_excel(csv_path)
                
                # Always create a sheet (df will never be None now)
                if df is not None and not df.empty:
                    # Clean sheet name (Excel has limitations on sheet names)
                    sheet_name = category_name[:31].replace('/', '_').replace('\\', '_').replace('*', '_').replace('[', '_').replace(']', '_').replace(':', '_').replace('?', '_')
                    
                    # Write to Excel sheet (we ensure df always has data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Log based on content
                    if 'Status' in df.columns and df['Status'].iloc[0] in ['Empty file', 'No columns', 'Error processing file']:
                        logger.warning(f"⚠ Created error sheet '{sheet_name}' for {csv_file}")
                    else:
                        logger.info(f"✓ Created sheet '{sheet_name}' with {len(df)} rows")
                else:
                    logger.warning(f"✗ Failed to create sheet for {csv_file} (unexpected error)")
            
            # Create price analysis sheet
            logger.info("Creating Price_Analysis sheet...")
            price_analysis = []
            for csv_file in sorted(csv_files):
                csv_path = os.path.join(csv_directory, csv_file)
                category_name = csv_file.replace('_data.csv', '').replace('_', ' ')
                
                try:
                    df = process_csv_for_excel(csv_path)
                    if df is not None and not df.empty and 'Price_AED' in df.columns:
                        # Sample some price data for analysis
                        aed_prices = df[df['Price_AED'] != '']['Price_AED'].head(5).tolist()
                        usd_prices = df[df['Price_USD'] != '']['Price_USD'].head(5).tolist()
                        
                        price_analysis.append({
                            'Category': category_name,
                            'Sample_AED_Prices': ', '.join(aed_prices) if aed_prices else 'N/A',
                            'Sample_USD_Prices': ', '.join(usd_prices) if usd_prices else 'N/A',
                            'Total_With_AED': len(df[df['Price_AED'] != '']),
                            'Total_With_USD': len(df[df['Price_USD'] != ''])
                        })
                except Exception as e:
                    logger.warning(f"Error processing {csv_file} for price analysis: {str(e)}")
            
            if price_analysis:
                price_df = pd.DataFrame(price_analysis)
                price_df.to_excel(writer, sheet_name='Price_Analysis', index=False)
                logger.info(f"✓ Created Price_Analysis sheet with {len(price_analysis)} categories")
            else:
                logger.warning("No price analysis data available")
        
        # Print summary
        total_items = sum(item['Total Items'] for item in summary_data)
        successful_categories = sum(1 for item in summary_data if item['Status'] == 'Success')
        
        logger.info(f"\n=== EXCEL CREATION SUMMARY ===")
        logger.info(f"Total CSV files processed: {len(csv_files)}")
        logger.info(f"Successful categories: {successful_categories}")
        logger.info(f"Total items: {total_items}")
        logger.info(f"Excel workbook saved to: {excel_path}")
        
        return excel_path
        
    except Exception as e:
        logger.error(f"Error creating Excel workbook: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("Starting Excel workbook creation from CSV files...")
    excel_path = create_excel_from_csv_files()
    
    if excel_path:
        logger.info(f"✓ Successfully created Excel workbook: {excel_path}")
    else:
        logger.error("✗ Failed to create Excel workbook") 