#!/usr/bin/env python3
"""
Specialized Automotive Parts Catalog Parser
Parses automotive parts catalogs with structured tabular data.
"""

import sys
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the parent directory to sys.path to import custom_logger
sys.path.append(str(Path(__file__).parent.parent))

from main import DocumentParser


class AutomotivePartsParser(DocumentParser):
    """Specialized parser for automotive parts catalogs."""
    
    def __init__(self, force_full_page_ocr: bool = True, enable_table_structure: bool = True):
        super().__init__(force_full_page_ocr, enable_table_structure)
        
    def _clean_part_number(self, text: str) -> str:
        """Clean and standardize part numbers."""
        if not text or pd.isna(text):
            return ""
        
        # Remove extra whitespace and standardize
        cleaned = str(text).strip()
        
        # Handle common patterns in automotive part numbers
        # Remove extra spaces around hyphens and slashes
        cleaned = re.sub(r'\s*[-/]\s*', '-', cleaned)
        
        # Standardize parentheses spacing
        cleaned = re.sub(r'\(\s*', '(', cleaned)
        cleaned = re.sub(r'\s*\)', ')', cleaned)
        
        return cleaned
    
    def _extract_part_code(self, text: str) -> tuple[str, str]:
        """
        Extract part number and code from text like "16546-EB70A xb".
        
        Returns:
            Tuple of (part_number, code)
        """
        if not text or pd.isna(text):
            return "", ""
        
        text = str(text).strip()
        
        # Pattern for part number + code (e.g., "16546-EB70A xb")
        pattern = r'^(.+?)\s+([a-zA-Z]{1,2})$'
        match = re.match(pattern, text)
        
        if match:
            part_number = self._clean_part_number(match.group(1))
            code = match.group(2).strip()
            return part_number, code
        
        # If no code pattern found, return the whole text as part number
        return self._clean_part_number(text), ""
    
    def _process_automotive_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process automotive parts table to extract structured data.
        
        Args:
            df: Raw DataFrame from OCR
            
        Returns:
            Processed DataFrame with structured columns
        """
        if df.empty:
            return df
        
        # Create a copy to avoid modifying original
        processed_df = df.copy()
        
        # Initialize new columns
        processed_df['Part_Number'] = ""
        processed_df['Part_Code'] = ""
        processed_df['Category'] = ""
        processed_df['Description'] = ""
        
        # Process each row
        for idx, row in processed_df.iterrows():
            # Get the first non-empty cell as the main content
            main_content = ""
            for col in processed_df.columns:
                if pd.notna(row[col]) and str(row[col]).strip():
                    main_content = str(row[col]).strip()
                    break
            
            if main_content:
                # Extract part number and code
                part_number, code = self._extract_part_code(main_content)
                
                processed_df.at[idx, 'Part_Number'] = part_number
                processed_df.at[idx, 'Part_Code'] = code
                processed_df.at[idx, 'Description'] = main_content
        
        # Remove empty rows
        processed_df = processed_df[processed_df['Part_Number'].str.len() > 0]
        
        return processed_df
    
    def _detect_table_category(self, table_df: pd.DataFrame) -> str:
        """
        Detect the category of automotive parts table.
        
        Args:
            table_df: DataFrame containing the table data
            
        Returns:
            Category name (e.g., "AIR FILTERS", "BRAKE PADS", etc.)
        """
        if table_df.empty:
            return "UNKNOWN"
        
        # Look for category indicators in the first few rows
        for idx in range(min(3, len(table_df))):
            for col in table_df.columns:
                cell_value = str(table_df.iloc[idx, col]).upper().strip()
                
                # Common automotive categories
                categories = [
                    "AIR FILTERS", "BALL JOINTS", "BRAKE PADS", "BRAKE SHOES",
                    "BRAKE MAST", "C.V. JOINTS", "CAM BUSHES", "CLUTCH COVERS",
                    "CLUTCH V. BOOSTER", "CONNECTING ROD", "CONROD BEARING",
                    "ENGINE PARTS", "TRANSMISSION", "SUSPENSION", "ELECTRICAL"
                ]
                
                for category in categories:
                    if category in cell_value:
                        return category
        
        return "UNKNOWN"
    
    def parse_automotive_document(self, input_path: str, output_dir: str = "automotive_output") -> Dict[str, Any]:
        """
        Parse automotive parts catalog document with specialized processing.
        
        Args:
            input_path: Path to the input document
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing parsing results and metadata
        """
        # First, parse the document using the base parser
        base_result = self.parse_document(input_path, output_dir)
        
        # Process each table for automotive-specific structure
        automotive_tables = []
        
        for table_info in base_result['tables_data']:
            if 'dataframe' in table_info:
                original_df = table_info['dataframe']
                
                # Detect table category
                category = self._detect_table_category(original_df)
                
                # Process the table for automotive structure
                processed_df = self._process_automotive_table(original_df)
                
                # Add category information
                processed_df['Category'] = category
                
                # Create automotive-specific table info
                automotive_table_info = {
                    'original_index': table_info['index'],
                    'category': category,
                    'original_rows': table_info['rows'],
                    'original_columns': table_info['columns'],
                    'processed_rows': len(processed_df),
                    'processed_columns': len(processed_df.columns),
                    'dataframe': processed_df,
                    'part_count': len(processed_df[processed_df['Part_Number'].str.len() > 0])
                }
                
                automotive_tables.append(automotive_table_info)
                
                # Save processed table
                doc_filename = Path(input_path).stem
                csv_filename = Path(output_dir) / f"{doc_filename}-{category.lower().replace(' ', '_')}-processed.csv"
                processed_df.to_csv(csv_filename, index=False)
                
                # Save summary
                summary_filename = Path(output_dir) / f"{doc_filename}-{category.lower().replace(' ', '_')}-summary.txt"
                with open(summary_filename, 'w') as f:
                    f.write(f"Category: {category}\n")
                    f.write(f"Total Parts: {automotive_table_info['part_count']}\n")
                    f.write(f"Original Rows: {table_info['rows']}\n")
                    f.write(f"Processed Rows: {len(processed_df)}\n")
                    f.write(f"Columns: {list(processed_df.columns)}\n\n")
                    f.write("Sample Parts:\n")
                    for _, row in processed_df.head(10).iterrows():
                        f.write(f"  {row['Part_Number']} - {row['Part_Code']}\n")
        
        # Create consolidated automotive parts list
        all_parts = []
        for table_info in automotive_tables:
            if 'dataframe' in table_info:
                df = table_info['dataframe']
                for _, row in df.iterrows():
                    if row['Part_Number']:
                        all_parts.append({
                            'Category': row['Category'],
                            'Part_Number': row['Part_Number'],
                            'Part_Code': row['Part_Code'],
                            'Description': row['Description'],
                            'Source_Table': table_info['category']
                        })
        
        # Save consolidated parts list
        if all_parts:
            consolidated_df = pd.DataFrame(all_parts)
            doc_filename = Path(input_path).stem
            consolidated_filename = Path(output_dir) / f"{doc_filename}-all-parts-consolidated.csv"
            consolidated_df.to_csv(consolidated_filename, index=False)
        
        # Update results with automotive-specific information
        automotive_result = base_result.copy()
        automotive_result.update({
            'automotive_tables': automotive_tables,
            'total_parts_found': len(all_parts),
            'categories_found': list(set(table['category'] for table in automotive_tables)),
            'consolidated_parts_file': str(consolidated_filename) if all_parts else None
        })
        
        return automotive_result


def main():
    """Example usage of the automotive parts parser."""
    print("🚗 Automotive Parts Catalog Parser")
    print("=" * 40)
    
    # Initialize the specialized parser
    parser = AutomotivePartsParser(
        force_full_page_ocr=True,
        enable_table_structure=True
    )
    
    # Example usage
    input_document = "automotive_catalog.pdf"  # Replace with your document
    output_directory = "automotive_parsed"
    
    if Path(input_document).exists():
        try:
            result = parser.parse_automotive_document(input_document, output_directory)
            
            print(f"✅ Automotive document parsed successfully!")
            print(f"📊 Total parts found: {result['total_parts_found']}")
            print(f"📋 Categories detected: {', '.join(result['categories_found'])}")
            print(f"📁 Output directory: {output_directory}")
            
            # Show details for each category
            for table_info in result['automotive_tables']:
                print(f"\n🔧 {table_info['category']}:")
                print(f"   Parts: {table_info['part_count']}")
                print(f"   CSV: {output_directory}/{Path(input_document).stem}-{table_info['category'].lower().replace(' ', '_')}-processed.csv")
            
            if result['consolidated_parts_file']:
                print(f"\n📋 Consolidated parts list: {result['consolidated_parts_file']}")
                
        except Exception as e:
            print(f"❌ Error parsing automotive document: {e}")
    else:
        print(f"⚠️  Document not found: {input_document}")
        print("Please place an automotive parts catalog document in the current directory.")


if __name__ == "__main__":
    main() 