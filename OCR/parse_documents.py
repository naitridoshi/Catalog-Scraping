#!/usr/bin/env python3
"""
Document Parser Script with User Confirmation
Parses documents in the documents directory after user confirmation.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to sys.path to import custom_logger
sys.path.append(str(Path(__file__).parent.parent))

from common.custom_logger import get_logger
from main import DocumentParser
from automotive_parts_parser import AutomotivePartsParser


class DocumentParserWithConfirmation:
    """Parser with user confirmation and custom logging."""
    
    def __init__(self, use_automotive_parser: bool = False):
        """
        Initialize the parser.
        
        Args:
            use_automotive_parser: Whether to use the specialized automotive parser
        """
        self.use_automotive_parser = use_automotive_parser
        self.logger, self.listener = get_logger("DocumentParser")
        self.listener.start()
        
        if use_automotive_parser:
            self.parser = AutomotivePartsParser(force_full_page_ocr=True, enable_table_structure=True)
            self.logger.info("🚗 Using specialized Automotive Parts Parser")
        else:
            self.parser = DocumentParser(force_full_page_ocr=True, enable_table_structure=True)
            self.logger.info("📄 Using standard Document Parser")
    
    def __del__(self):
        """Cleanup logger listener."""
        try:
            if hasattr(self, 'listener') and self.listener is not None:
                self.listener.stop()
        except Exception:
            pass  # Ignore cleanup errors
    
    def find_documents(self, documents_dir: str = "documents") -> List[Path]:
        """
        Find all supported documents in the documents directory.
        
        Args:
            documents_dir: Directory to search for documents
            
        Returns:
            List of document paths
        """
        documents_path = Path(documents_dir)
        
        if not documents_path.exists():
            self.logger.error(f"❌ Documents directory not found: {documents_dir}")
            return []
        
        # Supported document extensions
        supported_extensions = ['.pdf', '.docx', '.doc']
        documents = []
        
        for ext in supported_extensions:
            documents.extend(documents_path.glob(f"*{ext}"))
            documents.extend(documents_path.glob(f"*{ext.upper()}"))
        
        # Sort documents by name for consistent ordering
        documents.sort(key=lambda x: x.name)
        
        return documents
    
    def display_documents(self, documents: List[Path]) -> None:
        """
        Display found documents to the user.
        
        Args:
            documents: List of document paths
        """
        if not documents:
            self.logger.warning("⚠️  No documents found in the documents directory")
            return
        
        self.logger.info(f"📁 Found {len(documents)} document(s) in the documents directory:")
        
        for i, doc in enumerate(documents, 1):
            file_size = doc.stat().st_size / (1024 * 1024)  # Size in MB
            self.logger.info(f"   {i}. {doc.name} ({file_size:.1f} MB)")
    
    def ask_parser_type(self) -> bool:
        """
        Ask user which parser type to use.
        
        Returns:
            True for automotive parser, False for standard parser
        """
        print("\n" + "="*60)
        print("🔧 PARSER SELECTION")
        print("="*60)
        print("1. Standard Parser - General purpose, extracts all tables")
        print("2. Automotive Parser - Specialized for parts catalogs")
        print("\n" + "="*60)
        
        while True:
            response = input("❓ Which parser would you like to use? (1/2): ").strip()
            
            if response == "1":
                return False
            elif response == "2":
                return True
            else:
                print("❌ Please enter '1' or '2'")
    
    def ask_confirmation(self, documents: List[Path]) -> bool:
        """
        Ask user for confirmation to proceed with parsing.
        
        Args:
            documents: List of documents to be parsed
            
        Returns:
            True if user confirms, False otherwise
        """
        if not documents:
            return False
        
        print("\n" + "="*60)
        print("🔍 DOCUMENT PARSING CONFIRMATION")
        print("="*60)
        print(f"📄 Documents to parse: {len(documents)}")
        print(f"🔧 Parser type: {'Automotive Parts Parser' if self.use_automotive_parser else 'Standard Parser'}")
        print(f"📁 Output directory: {'automotive_output' if self.use_automotive_parser else 'output'}")
        print("\n📋 Documents:")
        
        for i, doc in enumerate(documents, 1):
            file_size = doc.stat().st_size / (1024 * 1024)
            print(f"   {i}. {doc.name} ({file_size:.1f} MB)")
        
        print("\n" + "="*60)
        
        while True:
            response = input("❓ Do you want to proceed with parsing? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y', 'confirm']:
                return True
            elif response in ['no', 'n', 'cancel']:
                return False
            else:
                print("❌ Please enter 'yes' or 'no'")
    
    def parse_documents(self, documents: List[Path]) -> List[Dict[str, Any]]:
        """
        Parse all documents and return results.
        
        Args:
            documents: List of document paths to parse
            
        Returns:
            List of parsing results
        """
        results = []
        total_documents = len(documents)
        
        self.logger.info(f"🚀 Starting to parse {total_documents} document(s)...")
        
        for i, doc_path in enumerate(documents, 1):
            try:
                self.logger.info(f"📄 Processing document {i}/{total_documents}: {doc_path.name}")
                
                # Choose output directory based on parser type
                output_dir = "automotive_output" if self.use_automotive_parser else "output"
                
                # Parse document
                if self.use_automotive_parser:
                    result = self.parser.parse_automotive_document(str(doc_path), output_dir)
                else:
                    result = self.parser.parse_document(str(doc_path), output_dir)
                
                # Log results
                self.logger.info(f"✅ Successfully parsed {doc_path.name}")
                self.logger.info(f"   📊 Tables found: {result['total_tables']}")
                self.logger.info(f"   ✅ Tables processed: {result['tables_processed']}")
                self.logger.info(f"   🖼️  Images detected: {result['total_images']}")
                self.logger.info(f"   ⏱️  Processing time: {result['processing_time']:.2f}s")
                
                if self.use_automotive_parser and 'total_parts_found' in result:
                    self.logger.info(f"   🔧 Total parts found: {result['total_parts_found']}")
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"❌ Error parsing {doc_path.name}: {e}")
                continue
        
        return results
    
    def display_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        Display summary of parsing results.
        
        Args:
            results: List of parsing results
        """
        if not results:
            self.logger.warning("⚠️  No documents were successfully parsed")
            return
        
        print("\n" + "="*60)
        print("📊 PARSING SUMMARY")
        print("=" * 60)
        
        total_documents = len(results)
        total_tables = sum(r['total_tables'] for r in results)
        total_processed = sum(r['tables_processed'] for r in results)
        total_time = sum(r['processing_time'] for r in results)
        total_images = sum(r['total_images'] for r in results)
        total_images_with_text = sum(r.get('images_with_text', 0) for r in results)
        
        print(f"📄 Documents processed: {total_documents}")
        print(f"📊 Total tables found: {total_tables}")
        print(f"✅ Total tables processed: {total_processed}")
        print(f"🖼️  Total images detected: {total_images}")
        print(f"📸 Images with extracted text: {total_images_with_text}")
        print(f"⏱️  Total processing time: {total_time:.2f}s")
        
        if self.use_automotive_parser:
            total_parts = sum(r.get('total_parts_found', 0) for r in results)
            print(f"🔧 Total parts extracted: {total_parts}")
        
        print("\n📁 Output files created:")
        for result in results:
            print(f"   📂 {result['output_directory']}")
            
            # Show specific files created
            doc_name = Path(result['input_file']).stem
            output_dir = Path(result['output_directory'])
            
            # Check for CSV files
            csv_files = list(output_dir.glob(f"{doc_name}-*.csv"))
            if csv_files:
                print(f"      📄 CSV files: {len(csv_files)}")
            
            # Check for text files
            text_files = list(output_dir.glob(f"{doc_name}-*.txt"))
            if text_files:
                print(f"      📝 Text files: {len(text_files)}")
            
            # Check for HTML files
            html_files = list(output_dir.glob(f"{doc_name}-*.html"))
            if html_files:
                print(f"      🌐 HTML files: {len(html_files)}")
        
        print("\n🎉 Parsing completed successfully!")


def main():
    """Main function to run the document parser with confirmation."""
    print("🚀 Document Parser with User Confirmation")
    print("=" * 50)
    
    try:
        # Find documents first
        temp_parser = DocumentParserWithConfirmation(use_automotive_parser=False)
        documents = temp_parser.find_documents()
        temp_parser.listener.stop()
        
        if not documents:
            print("❌ No documents found in the 'documents' directory.")
            print("💡 Please place your documents in the 'documents' directory and try again.")
            return
        
        # Ask user which parser to use
        use_automotive = temp_parser.ask_parser_type()
        
        # Initialize parser with custom logger
        parser_manager = DocumentParserWithConfirmation(use_automotive_parser=use_automotive)
        
        # Display found documents
        parser_manager.display_documents(documents)
        
        # Ask for confirmation
        if not parser_manager.ask_confirmation(documents):
            print("❌ Parsing cancelled by user.")
            return
        
        # Parse documents
        results = parser_manager.parse_documents(documents)
        
        # Display summary
        parser_manager.display_summary(results)
        
    except KeyboardInterrupt:
        print("\n❌ Parsing interrupted by user.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        # Cleanup
        if 'temp_parser' in locals():
            try:
                temp_parser.listener.stop()
            except:
                pass
        if 'parser_manager' in locals():
            try:
                parser_manager.listener.stop()
            except:
                pass


if __name__ == "__main__":
    main() 