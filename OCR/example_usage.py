#!/usr/bin/env python3
"""
Example usage of the Document Parser
Demonstrates how to parse documents containing images with tabular data.
"""

import os
from pathlib import Path
from main import DocumentParser


def example_single_document():
    """Example: Parse a single document."""
    print("=== Single Document Parsing Example ===")
    
    # Initialize parser with full page OCR and table structure detection
    parser = DocumentParser(
        force_full_page_ocr=True,
        enable_table_structure=True
    )
    
    # Example paths (replace with your actual document paths)
    input_document = "sample_document.pdf"  # or "sample_document.docx"
    output_directory = "parsed_output"
    
    if os.path.exists(input_document):
        try:
            # Parse the document
            result = parser.parse_document(input_document, output_directory)
            
            # Print results
            print(f"✅ Document parsed successfully!")
            print(f"📁 Input file: {result['input_file']}")
            print(f"📂 Output directory: {result['output_directory']}")
            print(f"⏱️  Processing time: {result['processing_time']:.2f} seconds")
            print(f"📊 Tables found: {result['total_tables']}")
            print(f"✅ Tables processed: {result['tables_processed']}")
            print(f"🖼️  Images detected: {result['total_images']}")
            
            # Show table details
            for i, table_info in enumerate(result['tables_data']):
                if 'dataframe' in table_info:
                    df = table_info['dataframe']
                    print(f"\n📋 Table {i+1}:")
                    print(f"   Rows: {table_info['rows']}, Columns: {table_info['columns']}")
                    print(f"   CSV file: {output_directory}/sample_document-table-{i+1}.csv")
                    print(f"   HTML file: {output_directory}/sample_document-table-{i+1}.html")
                    
        except Exception as e:
            print(f"❌ Error parsing document: {e}")
    else:
        print(f"⚠️  Sample document not found: {input_document}")
        print("Please place a PDF or Word document in the current directory to test.")


def example_multiple_documents():
    """Example: Parse multiple documents in a directory."""
    print("\n=== Multiple Documents Parsing Example ===")
    
    parser = DocumentParser(
        force_full_page_ocr=True,
        enable_table_structure=True
    )
    
    # Example paths
    input_directory = "documents"  # Directory containing multiple documents
    output_directory = "batch_output"
    
    if os.path.exists(input_directory):
        try:
            # Parse all documents in the directory
            results = parser.parse_multiple_documents(input_directory, output_directory)
            
            print(f"✅ Batch processing completed!")
            print(f"📁 Input directory: {input_directory}")
            print(f"📂 Output directory: {output_directory}")
            print(f"📄 Documents processed: {len(results)}")
            
            # Summary of results
            total_tables = sum(r['total_tables'] for r in results)
            total_processed = sum(r['tables_processed'] for r in results)
            total_time = sum(r['processing_time'] for r in results)
            
            print(f"📊 Total tables found: {total_tables}")
            print(f"✅ Total tables processed: {total_processed}")
            print(f"⏱️  Total processing time: {total_time:.2f} seconds")
            
        except Exception as e:
            print(f"❌ Error in batch processing: {e}")
    else:
        print(f"⚠️  Input directory not found: {input_directory}")
        print("Please create a 'documents' directory with PDF/Word files to test.")


def example_custom_configuration():
    """Example: Custom configuration for specific use cases."""
    print("\n=== Custom Configuration Example ===")
    
    # Example 1: Fast processing (no table structure detection)
    fast_parser = DocumentParser(
        force_full_page_ocr=True,
        enable_table_structure=False
    )
    print("🔧 Fast parser configured (no table structure detection)")
    
    # Example 2: High accuracy processing
    accurate_parser = DocumentParser(
        force_full_page_ocr=True,
        enable_table_structure=True
    )
    print("🔧 Accurate parser configured (with table structure detection)")
    
    # Example usage with custom parser
    # result = accurate_parser.parse_document("document.pdf", "accurate_output")


def create_sample_structure():
    """Create sample directory structure for testing."""
    print("\n=== Creating Sample Directory Structure ===")
    
    # Create directories
    directories = ["documents", "parsed_output", "batch_output"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Created directory: {directory}")
    
    # Create a sample README
    readme_content = """# Document Parser Test Directory

This directory contains sample documents for testing the Docling document parser.

## Usage:
1. Place PDF or Word documents in the 'documents' directory
2. Run the parser to extract tables to CSV files
3. Check the output directories for results

## Supported formats:
- PDF files (.pdf)
- Word documents (.docx, .doc)

## Expected output:
- CSV files for each detected table
- HTML files for table visualization
- Markdown files for full document content
"""
    
    with open("README.md", "w") as f:
        f.write(readme_content)
    
    print("📝 Created README.md with usage instructions")


def main():
    """Main function demonstrating all examples."""
    print("🚀 Docling Document Parser - Example Usage")
    print("=" * 50)
    
    # Create sample directory structure
    create_sample_structure()
    
    # Show examples
    example_single_document()
    example_multiple_documents()
    example_custom_configuration()
    
    print("\n" + "=" * 50)
    print("📚 For more information, see the main.py file and Docling documentation:")
    print("   https://docling-project.github.io/docling/")
    print("\n🎯 To get started:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Place your documents in the 'documents' directory")
    print("   3. Run: python example_usage.py")
    print("   4. Check the output directories for results")


if __name__ == "__main__":
    main() 