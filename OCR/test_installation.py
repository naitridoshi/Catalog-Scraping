#!/usr/bin/env python3
"""
Test script to verify Docling document parser installation and basic functionality.
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import pandas as pd
        print("✅ pandas imported successfully")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False
    
    try:
        from pathlib import Path
        print("✅ pathlib imported successfully")
    except ImportError as e:
        print(f"❌ pathlib import failed: {e}")
        return False
    
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
        print("✅ docling imported successfully")
    except ImportError as e:
        print(f"❌ docling import failed: {e}")
        print("💡 Try installing docling: pip install docling")
        return False
    
    try:
        from main import DocumentParser
        print("✅ DocumentParser imported successfully")
    except ImportError as e:
        print(f"❌ DocumentParser import failed: {e}")
        return False
    
    try:
        from automotive_parts_parser import AutomotivePartsParser
        print("✅ AutomotivePartsParser imported successfully")
    except ImportError as e:
        print(f"❌ AutomotivePartsParser import failed: {e}")
        return False
    
    return True


def test_basic_functionality():
    """Test basic parser functionality without processing documents."""
    print("\n🔍 Testing basic functionality...")
    
    try:
        from main import DocumentParser
        
        # Test parser initialization
        parser = DocumentParser(force_full_page_ocr=True, enable_table_structure=True)
        print("✅ Parser initialized successfully")
        
        # Test pipeline options creation
        pdf_options = parser._create_pdf_pipeline_options()
        print("✅ PDF pipeline options created successfully")
        
        # Test converter creation
        converter = parser._create_converter()
        print("✅ Document converter created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False


def test_file_structure():
    """Test if all required files exist."""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "example_usage.py",
        "automotive_parts_parser.py"
    ]
    
    all_files_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            all_files_exist = False
    
    return all_files_exist


def test_tesseract_installation():
    """Test if Tesseract OCR is available."""
    print("\n🔍 Testing Tesseract OCR installation...")
    
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Tesseract OCR is installed and working")
            print(f"   Version: {result.stdout.strip()}")
            return True
        else:
            print("❌ Tesseract OCR is not working properly")
            return False
    except FileNotFoundError:
        print("❌ Tesseract OCR is not installed")
        print("💡 Install Tesseract:")
        print("   Ubuntu/Debian: sudo apt-get install tesseract-ocr")
        print("   macOS: brew install tesseract")
        print("   Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        print(f"❌ Error testing Tesseract: {e}")
        return False


def create_sample_directories():
    """Create sample directories for testing."""
    print("\n🔍 Creating sample directories...")
    
    directories = ["documents", "output", "automotive_output"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")


def main():
    """Run all tests."""
    print("🚀 Docling Document Parser - Installation Test")
    print("=" * 50)
    
    # Run all tests
    tests = [
        ("Import Test", test_imports),
        ("Basic Functionality Test", test_basic_functionality),
        ("File Structure Test", test_file_structure),
        ("Tesseract OCR Test", test_tesseract_installation),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            passed_tests += 1
        else:
            print(f"❌ {test_name} failed")
    
    # Create sample directories
    create_sample_directories()
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! The parser is ready to use.")
        print("\n📚 Next steps:")
        print("   1. Place your documents in the 'documents' directory")
        print("   2. Run: python example_usage.py")
        print("   3. Check the output directories for results")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        print("\n🔧 Troubleshooting:")
        print("   1. Install missing dependencies: pip install -r requirements.txt")
        print("   2. Install Tesseract OCR (see error messages above)")
        print("   3. Ensure all files are in the correct directory")
    
    print("\n📖 For more information, see README.md")


if __name__ == "__main__":
    main() 