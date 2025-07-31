# Document Image Extraction and OCR

This tool extracts images from PDFs, Word documents, and processes standalone images using EasyOCR to extract text data into CSV format. It also supports handwritten document processing using LLMWhisperer.

## Features

- ✅ Extracts images from PDFs, Word documents (.pdf, .docx, .doc)
- ✅ Processes standalone images (.png, .jpg, .jpeg, .gif, .bmp, .tiff, .webp)
- ✅ Performs OCR using EasyOCR (much better than Tesseract for this use case)
- ✅ Handles handwritten documents using LLMWhisperer (requires API key)
- ✅ Exports results to CSV and text files
- ✅ Saves extracted images as PNG files
- ✅ Provides detailed logging and progress information
- ✅ Asks for confirmation before processing files
- ✅ Supports batch processing of multiple files

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up LLMWhisperer API key (optional, for handwritten documents):
   
   Option A: Environment variable:
   ```bash
   export LLMWHISPERER_API_KEY='your_api_key_here'
   ```
   
   Option B: Create a `.env` file in the OCR directory:
   ```
   LLMWHISPERER_API_KEY=your_api_key_here
   ```

## Usage

Simply run the main script:
```bash
python main.py
```

The script will:
1. Find all supported files in the `documents/` directory
2. Show you the list of files to be processed
3. Ask for confirmation before starting
4. Extract images from documents (PDFs, Word) or process standalone images
5. Perform OCR on all images using EasyOCR
6. If LLMWhisperer API key is set, process files in `handwritten_documents/` directory
7. Save results to the `output/` directory

## Directory Structure

```
OCR/
├── documents/              # Regular documents (PDF, Word, Images)
├── handwritten_documents/  # Handwritten documents (requires API key)
├── output/                # Results directory
├── main.py                # Main script
├── requirements.txt       # Dependencies
└── README.md             # This file
```

## Supported File Types

### Documents
- **PDF files** (.pdf) - Extracts embedded images and performs OCR
- **Word documents** (.docx, .doc) - Extracts embedded images and performs OCR

### Images
- **PNG** (.png)
- **JPEG** (.jpg, .jpeg)
- **GIF** (.gif)
- **BMP** (.bmp)
- **TIFF** (.tiff)
- **WebP** (.webp)

## Output Files

For each processed file, you'll get:
- `{filename}-ocr-results.csv` - OCR results in CSV format (regular documents)
- `{filename}-ocr-results.txt` - OCR results in text format (regular documents)
- `{filename}-llmwhisperer-results.csv` - LLMWhisperer results in CSV format (handwritten documents)
- `{filename}-llmwhisperer-results.txt` - LLMWhisperer results in text format (handwritten documents)
- `extracted_images/` - Directory containing the extracted images (for documents)

## LLMWhisperer Integration

For handwritten document processing, the tool integrates with [LLMWhisperer](https://docs.unstract.com/llmwhisperer/llm_whisperer/llm_whisperer_modes/) using the `high_quality` mode, which is optimized for:

- Handwritten documents
- Low-quality scanned documents
- Documents with complex layouts
- Documents requiring AI/ML enhancement

### LLMWhisperer Supported File Types

According to the [LLMWhisperer documentation](https://docs.unstract.com/llmwhisperer/llm_whisperer/llm_whisperer_modes/), the following file types are supported:

- **PDF files** (scanned and native text)
- **Images** (PNG, JPEG, GIF, BMP, TIFF, WebP)
- **MS Office documents** (Word, PowerPoint, but not Excel)
- **LibreOffice documents** (Writer, Calc, Impress)

**Note**: Some file types may be rejected by the API depending on their format or content.

### LLMWhisperer Modes Available

Based on the [LLMWhisperer documentation](https://docs.unstract.com/llmwhisperer/llm_whisperer/llm_whisperer_modes/):

- **`high_quality`** - Best for handwritten documents (default for handwritten processing)
- **`low_cost`** - Good for clean scanned documents
- **`form`** - For documents with forms and checkboxes
- **`table`** - For documents with structured tables
- **`native_text`** - Fastest for digital text PDFs

## Requirements

- Python 3.8+
- EasyOCR
- Docling
- Pandas
- Pillow
- Requests (for LLMWhisperer API calls)

## Environment Variables

- `LLMWHISPERER_API_KEY` - Required for handwritten document processing

## Notes

- EasyOCR provides much better results than Tesseract for this type of content
- The tool uses the `pil_image` attribute from Docling to extract images from documents
- Processing time depends on the number and size of images in the documents
- The script asks for confirmation before processing to prevent accidental runs
- All supported file types are automatically detected and processed appropriately
- LLMWhisperer processing requires an API key from the environment variable 