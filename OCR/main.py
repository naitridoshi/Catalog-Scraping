#!/usr/bin/env python3
"""
Document Image Extraction and OCR
Extracts images from PDFs, Word documents, processes standalone images using EasyOCR,
and handles handwritten documents using LLMWhisperer.
"""

import sys
import time
import os
import base64
import requests
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import io
from PIL import Image
import easyocr
from dotenv import load_dotenv

# Add the parent directory to sys.path to import custom_logger
sys.path.append(str(Path(__file__).parent.parent))

from common.custom_logger import get_logger
from docling.datamodel.base_models import InputFormat
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend


class LLMWhispererClient:
    """Client for LLMWhisperer API for handwritten document processing."""
    
    def __init__(self, api_key: str):
        """Initialize LLMWhisperer client."""
        self.api_key = api_key
        self.base_url = "https://llmwhisperer-api.us-central.unstract.com/api/v2"
        self.headers = {"unstract-key": api_key}
        self.logger, self.listener = get_logger("LLMWhispererClient")
        self.listener.start()
    
    def __del__(self):
        """Cleanup logger listener."""
        try:
            if hasattr(self, 'listener') and self.listener is not None:
                self.listener.stop()
        except Exception:
            pass
    
    def extract_text(self, file_path: Path, mode: str = None, output_mode: str = "layout_preserving") -> Dict[str, Any]:
        """
        Extract text from document using LLMWhisperer API.
        
        Args:
            file_path: Path to the document
            mode: Processing mode (high_quality for handwritten docs)
            output_mode: Output mode (layout_preserving or text)
            
        Returns:
            Dictionary containing extraction results
        """
        try:
            self.logger.info(f"🚀 Starting LLMWhisperer extraction: {file_path.name}")
            
            # Prepare the API request
            url = f"{self.base_url}/whisper"
            
            # Auto-select mode based on file type
            if mode is None:
                if file_path.suffix.lower() in ['.docx', '.doc']:
                    mode = "low_cost"  # Try low_cost for Word documents
                else:
                    mode = "high_quality"  # Default for other files
            
            params = {
                "mode": mode,
                "output_mode": output_mode,
                "page_seperator": "<<<",
                "tag": "handwritten_documents"
            }
            
            # Read the file
            with open(file_path, 'rb') as f:
                file_content = f.read()
                file_size = len(file_content)
                self.logger.info(f"📄 File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
                self.logger.info(f"📄 File extension: {file_path.suffix}")
                
                # Check file size (LLMWhisperer might have limits)
                if file_size > 10 * 1024 * 1024:  # 10MB limit
                    self.logger.warning(f"⚠️  File size ({file_size/1024/1024:.2f} MB) might be too large")
                
                # Use appropriate MIME type based on file extension
                if file_path.suffix.lower() == '.docx':
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif file_path.suffix.lower() == '.png':
                    mime_type = 'image/png'
                elif file_path.suffix.lower() in ['.jpg', '.jpeg']:
                    mime_type = 'image/jpeg'
                elif file_path.suffix.lower() == '.gif':
                    mime_type = 'image/gif'
                elif file_path.suffix.lower() == '.bmp':
                    mime_type = 'image/bmp'
                elif file_path.suffix.lower() in ['.tif', '.tiff']:
                    mime_type = 'image/tiff'
                elif file_path.suffix.lower() == '.webp':
                    mime_type = 'image/webp'
                else:
                    mime_type = 'application/octet-stream'
                
                # Send file content directly in request body as per API documentation
                # The API expects binary data in application/octet-stream format
                self.logger.info(f"🌐 Making API call to: {url}")
                self.logger.info(f"📋 Parameters: {params}")
                response = requests.post(url, headers=self.headers, params=params, data=file_content)
                
                if response.status_code == 202:
                    result = response.json()
                    whisper_hash = result.get('whisper_hash')
                    self.logger.info(f"✅ Document accepted for processing. Hash: {whisper_hash[:20]}...")
                    
                    # Poll for completion
                    return self._poll_for_completion(whisper_hash, file_path.name)
                else:
                    self.logger.error(f"❌ API call failed: {response.status_code} - {response.text}")
                    return {"error": f"API call failed: {response.status_code} - {response.text}", "status": "error"}
                    
        except Exception as e:
            self.logger.error(f"❌ Error in LLMWhisperer extraction: {e}")
            return {"error": str(e), "status": "error"}
    
    def _poll_for_completion(self, whisper_hash: str, filename: str) -> Dict[str, Any]:
        """
        Poll for completion of the extraction process.
        
        Args:
            whisper_hash: The whisper hash from the initial request
            filename: Original filename
            
        Returns:
            Dictionary containing the final results
        """
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Check status
                status_url = f"{self.base_url}/whisper-status"
                status_response = requests.get(status_url, headers=self.headers, params={"whisper_hash": whisper_hash})
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status')
                    self.logger.info(f"📊 Status response: {status_data}")
                    
                    if status == 'processed':
                        self.logger.info(f"✅ Processing completed for {filename}")
                        # Retrieve the results
                        return self._retrieve_results(whisper_hash, filename, status_data)
                    elif status == 'error':
                        error_msg = status_data.get('message', status_data.get('error', 'Unknown error'))
                        self.logger.error(f"❌ Processing failed for {filename}: {error_msg}")
                        return {"error": error_msg, "status": "error", "filename": filename, "status_data": status_data}
                    else:
                        self.logger.info(f"⏳ Processing {filename}: {status} (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(5)
                        attempt += 1
                else:
                    self.logger.error(f"❌ Status check failed: {status_response.status_code}")
                    return {"error": "Status check failed", "status": "error", "filename": filename}
                    
            except Exception as e:
                self.logger.error(f"❌ Error checking status: {e}")
                return {"error": str(e), "status": "error", "filename": filename}
        
        self.logger.error(f"❌ Timeout waiting for completion of {filename}")
        return {"error": "Processing timeout", "status": "timeout", "filename": filename}
    
    def _retrieve_results(self, whisper_hash: str, filename: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve the final extraction results.
        
        Args:
            whisper_hash: The whisper hash
            filename: Original filename
            status_data: Status response data
            
        Returns:
            Dictionary containing the extracted text and metadata
        """
        try:
            # Retrieve the extracted text
            retrieve_url = f"{self.base_url}/whisper-retrieve"
            retrieve_response = requests.get(retrieve_url, headers=self.headers, params={"whisper_hash": whisper_hash})
            
            if retrieve_response.status_code == 200:
                text_data = retrieve_response.json()
                extracted_text = text_data.get('result_text', '')  # Use 'result_text' instead of 'text'
                
                # Log the full response for debugging
                self.logger.info(f"📄 Retrieved text data: {text_data}")
                self.logger.info(f"📄 Extracted text length: {len(extracted_text)}")
                if extracted_text:
                    self.logger.info(f"📄 Sample text: {extracted_text[:200]}...")
                else:
                    self.logger.warning(f"⚠️  No text extracted from {filename}")
                
                # Get details for additional metadata
                detail_url = f"{self.base_url}/whisper-detail"
                detail_response = requests.get(detail_url, headers=self.headers, params={"whisper_hash": whisper_hash})
                
                details = {}
                if detail_response.status_code == 200:
                    details = detail_response.json()
                    self.logger.info(f"📄 Details response: {details}")
                
                return {
                    "status": "success",
                    "filename": filename,
                    "extracted_text": extracted_text,
                    "text_length": len(extracted_text),
                    "whisper_hash": whisper_hash,
                    "status_data": status_data,
                    "details": details
                }
            else:
                self.logger.error(f"❌ Failed to retrieve results: {retrieve_response.status_code}")
                return {"error": "Failed to retrieve results", "status": "error", "filename": filename}
                
        except Exception as e:
            self.logger.error(f"❌ Error retrieving results: {e}")
            return {"error": str(e), "status": "error", "filename": filename}


class DocumentImageOCRParser:
    """Parser that extracts images from documents and performs OCR using EasyOCR."""
    
    def __init__(self, llmwhisperer_api_key: Optional[str] = None):
        """Initialize the parser."""
        self.logger, self.listener = get_logger("DocumentImageOCRParser")
        self.listener.start()
        
        # Initialize EasyOCR reader
        try:
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            self.logger.info("✅ EasyOCR initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ EasyOCR initialization failed: {e}")
            raise
        
        # Initialize LLMWhisperer client if API key provided
        self.llmwhisperer_client = None
        if llmwhisperer_api_key:
            try:
                self.llmwhisperer_client = LLMWhispererClient(llmwhisperer_api_key)
                self.logger.info("✅ LLMWhisperer client initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ LLMWhisperer client initialization failed: {e}")
    
    def __del__(self):
        """Cleanup logger listener."""
        try:
            if hasattr(self, 'listener') and self.listener is not None:
                self.listener.stop()
        except Exception:
            pass
    
    def _create_converter(self) -> DocumentConverter:
        """Create document converter for all supported formats."""
        converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.IMAGE,
                InputFormat.DOCX,
                InputFormat.HTML,
                InputFormat.PPTX,
                InputFormat.ASCIIDOC,
                InputFormat.CSV,
                InputFormat.MD,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline, 
                    backend=PyPdfiumDocumentBackend
                ),
                InputFormat.DOCX: WordFormatOption(
                    pipeline_cls=SimplePipeline
                ),
            },
        )
        
        self.logger.info("🔧 Using Docling converter for document processing")
        return converter
    
    def _extract_images_from_document(self, doc, output_dir: Path, doc_filename: str) -> List[Dict[str, Any]]:
        """
        Extract images from document using the pil_image attribute.
        
        Args:
            doc: Document object from Docling
            output_dir: Output directory for images
            doc_filename: Document filename
            
        Returns:
            List of extracted image information
        """
        extracted_images = []
        images_dir = output_dir / "extracted_images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"📸 Extracting {len(doc.pictures)} images from document")
        
        for i, picture in enumerate(doc.pictures):
            try:
                self.logger.info(f"🔍 Processing image {i+1}...")
                
                image_info = {
                    'index': i,
                    'filename': None,
                    'filepath': None,
                    'width': None,
                    'height': None,
                    'format': None,
                    'size_bytes': None
                }
                
                # Extract using PIL image
                if hasattr(picture, 'image') and picture.image:
                    if hasattr(picture.image, 'pil_image') and picture.image.pil_image:
                        try:
                            pil_image = picture.image.pil_image
                            
                            # Get image properties
                            image_info['width'] = pil_image.width
                            image_info['height'] = pil_image.height
                            image_info['format'] = pil_image.format
                            
                            # Save image
                            extension = pil_image.format.lower() if pil_image.format else 'png'
                            image_filename = f"{doc_filename}-image-{i+1:03d}.{extension}"
                            image_path = images_dir / image_filename
                            
                            pil_image.save(image_path)
                            image_info['filename'] = image_filename
                            image_info['filepath'] = str(image_path)
                            image_info['size_bytes'] = os.path.getsize(image_path)
                            
                            self.logger.info(f"💾 Saved image {i+1}: {image_filename} ({pil_image.width}x{pil_image.height})")
                            extracted_images.append(image_info)
                            
                        except Exception as e:
                            self.logger.error(f"❌ Error saving image {i+1}: {e}")
                    else:
                        self.logger.warning(f"⚠️  Image {i+1}: No PIL image found")
                else:
                    self.logger.warning(f"⚠️  Image {i+1}: No image object found")
                        
            except Exception as e:
                self.logger.error(f"❌ Error processing image {i+1}: {e}")
        
        self.logger.info(f"✅ Successfully extracted {len(extracted_images)} images")
        return extracted_images
    
    def _process_standalone_image(self, image_path: Path, output_dir: Path) -> List[Dict[str, Any]]:
        """
        Process a standalone image file.
        
        Args:
            image_path: Path to the image file
            output_dir: Output directory
            
        Returns:
            List containing the image information
        """
        try:
            # Open image to get properties
            with Image.open(image_path) as pil_image:
                image_info = {
                    'index': 0,
                    'filename': image_path.name,
                    'filepath': str(image_path),
                    'width': pil_image.width,
                    'height': pil_image.height,
                    'format': pil_image.format,
                    'size_bytes': os.path.getsize(image_path)
                }
            
            self.logger.info(f"📸 Processing standalone image: {image_path.name} ({image_info['width']}x{image_info['height']})")
            return [image_info]
            
        except Exception as e:
            self.logger.error(f"❌ Error processing standalone image {image_path}: {e}")
            return []
    
    def _perform_ocr_on_image(self, image_path: Path) -> str:
        """
        Perform OCR on an image using EasyOCR.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Extracted text from the image
        """
        try:
            # Use EasyOCR
            results = self.easyocr_reader.readtext(str(image_path))
            text = '\n'.join([result[1] for result in results])
            return text.strip()
                
        except Exception as e:
            self.logger.error(f"❌ OCR error on {image_path}: {e}")
            return ""
    
    def _perform_ocr_on_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform OCR on all images.
        
        Args:
            images: List of image information
            
        Returns:
            List of images with OCR results
        """
        ocr_results = []
        
        self.logger.info(f"🔍 Performing EasyOCR on {len(images)} images")
        
        for image_info in images:
            if image_info['filepath']:
                image_path = Path(image_info['filepath'])
                
                if image_path.exists():
                    # Perform OCR
                    extracted_text = self._perform_ocr_on_image(image_path)
                    
                    # Add OCR results to image info
                    image_info['ocr_text'] = extracted_text
                    image_info['ocr_type'] = 'easyocr'
                    image_info['text_length'] = len(extracted_text)
                    image_info['has_text'] = len(extracted_text.strip()) > 0
                    
                    if extracted_text:
                        self.logger.info(f"📸 Image {image_info['index']+1}: {len(extracted_text)} characters extracted")
                    else:
                        self.logger.warning(f"⚠️  Image {image_info['index']+1}: No text extracted")
                    
                    ocr_results.append(image_info)
                else:
                    self.logger.error(f"❌ Image file not found: {image_path}")
        
        return ocr_results
    
    def _create_csv_from_ocr_results(self, ocr_results: List[Dict[str, Any]], output_dir: Path, doc_filename: str) -> None:
        """
        Create CSV files from OCR results.
        
        Args:
            ocr_results: List of OCR results
            output_dir: Output directory
            doc_filename: Document filename
        """
        if not ocr_results:
            return
        
        # Create a DataFrame from the OCR results
        df_data = []
        for item in ocr_results:
            if item.get('ocr_text'):
                # Split text into lines and create rows
                lines = item['ocr_text'].split('\n')
                for line_num, line in enumerate(lines):
                    if line.strip():  # Only add non-empty lines
                        df_data.append({
                            'Image_Index': item['index'] + 1,
                            'Image_Filename': item.get('filename', 'unknown'),
                            'Line_Number': line_num + 1,
                            'Text': line.strip(),
                            'OCR_Type': 'EasyOCR',
                            'Image_Width': item.get('width'),
                            'Image_Height': item.get('height'),
                            'Image_Format': item.get('format'),
                            'Image_Size_Bytes': item.get('size_bytes')
                        })
        
        if df_data:
            df = pd.DataFrame(df_data)
            csv_filename = output_dir / f"{doc_filename}-ocr-results.csv"
            df.to_csv(csv_filename, index=False)
            self.logger.info(f"💾 Saved OCR results to {csv_filename}")
            
            # Also save as a simple text file
            text_filename = output_dir / f"{doc_filename}-ocr-results.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                for item in ocr_results:
                    if item.get('ocr_text'):
                        f.write(f"=== Image {item['index'] + 1}: {item.get('filename', 'unknown')} ===\n")
                        f.write(f"OCR Type: EasyOCR\n")
                        f.write(f"Dimensions: {item.get('width')}x{item.get('height')}\n")
                        f.write(f"Format: {item.get('format', 'unknown')}\n")
                        f.write(item['ocr_text'])
                        f.write("\n\n")
            self.logger.info(f"💾 Saved OCR results to {text_filename}")
    
    def _create_csv_from_llmwhisperer_results(self, llmwhisperer_results: List[Dict[str, Any]], output_dir: Path, doc_filename: str) -> None:
        """
        Create CSV files from LLMWhisperer results.
        
        Args:
            llmwhisperer_results: List of LLMWhisperer extraction results
            output_dir: Output directory
            doc_filename: Document filename
        """
        if not llmwhisperer_results:
            return
        
        # Create a DataFrame from the LLMWhisperer results
        df_data = []
        
        for result in llmwhisperer_results:
            if result.get('status') == 'success':
                extracted_text = result.get('extracted_text', '')
                image_info = result.get('image_info', {})
                image_index = result.get('image_index', 0)
                
                if extracted_text:
                    lines = extracted_text.split('\n')
                    for line_num, line in enumerate(lines):
                        if line.strip():  # Only add non-empty lines
                            df_data.append({
                                'Image_Index': image_index + 1,
                                'Image_Filename': image_info.get('filename', 'unknown'),
                                'Line_Number': line_num + 1,
                                'Text': line.strip(),
                                'OCR_Type': 'LLMWhisperer',
                                'Processing_Mode': 'high_quality',
                                'Output_Mode': 'layout_preserving',
                                'Image_Width': image_info.get('width'),
                                'Image_Height': image_info.get('height'),
                                'Image_Format': image_info.get('format'),
                                'Image_Size_Bytes': image_info.get('size_bytes')
                            })
        
        if df_data:
            df = pd.DataFrame(df_data)
            csv_filename = output_dir / f"{doc_filename}-llmwhisperer-results.csv"
            df.to_csv(csv_filename, index=False)
            self.logger.info(f"💾 Saved LLMWhisperer results to {csv_filename}")
            
            # Also save as a simple text file
            text_filename = output_dir / f"{doc_filename}-llmwhisperer-results.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(f"=== LLMWhisperer Results for {doc_filename} ===\n")
                f.write(f"Total Images Processed: {len(llmwhisperer_results)}\n")
                f.write(f"Successful Extractions: {len([r for r in llmwhisperer_results if r.get('status') == 'success'])}\n")
                f.write("=" * 50 + "\n\n")
                
                for i, result in enumerate(llmwhisperer_results):
                    if result.get('status') == 'success':
                        image_info = result.get('image_info', {})
                        extracted_text = result.get('extracted_text', '')
                        
                        f.write(f"=== Image {i+1}: {image_info.get('filename', 'unknown')} ===\n")
                        f.write(f"OCR Type: LLMWhisperer\n")
                        f.write(f"Processing Mode: high_quality\n")
                        f.write(f"Dimensions: {image_info.get('width')}x{image_info.get('height')}\n")
                        f.write(f"Format: {image_info.get('format', 'unknown')}\n")
                        f.write(f"Text Length: {len(extracted_text)} characters\n")
                        f.write(extracted_text)
                        f.write("\n\n")
                    else:
                        image_info = result.get('image_info', {})
                        f.write(f"=== Image {i+1}: {image_info.get('filename', 'unknown')} ===\n")
                        f.write(f"Status: Failed\n")
                        f.write(f"Error: {result.get('error', 'Unknown error')}\n\n")
            
            self.logger.info(f"💾 Saved LLMWhisperer results to {text_filename}")
    
    def parse_document(self, input_path: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        Parse document by extracting images and performing OCR.
        
        Args:
            input_path: Path to the input document
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing parsing results and metadata
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        self.logger.info(f"🚀 Starting image extraction and OCR parsing: {input_path}")
        start_time = time.time()
        
        # Check if it's a standalone image
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        if input_path.suffix.lower() in image_extensions:
            # Process standalone image
            images = self._process_standalone_image(input_path, output_dir)
            doc_filename = input_path.stem
        else:
            # Process document (PDF, Word, etc.)
            converter = self._create_converter()
            conv_result = converter.convert(input_path)
            doc = conv_result.document
            doc_filename = input_path.stem
            
            # Extract images from document
            images = self._extract_images_from_document(doc, output_dir, doc_filename)
        
        # Perform OCR on images
        ocr_results = self._perform_ocr_on_images(images)
        
        # Create CSV from OCR results
        self._create_csv_from_ocr_results(ocr_results, output_dir, doc_filename)
        
        end_time = time.time() - start_time
        
        # Calculate statistics
        images_with_text = len([img for img in ocr_results if img.get('has_text', False)])
        total_text_length = sum([img.get('text_length', 0) for img in ocr_results])
        
        # Prepare results
        results = {
            'input_file': str(input_path),
            'output_directory': str(output_dir),
            'processing_time': end_time,
            'total_images_found': len(images),
            'images_extracted': len(images),
            'images_with_text': images_with_text,
            'total_text_length': total_text_length,
            'ocr_results': ocr_results,
            'extracted_images': images
        }
        
        self.logger.info(f"✅ Image extraction and OCR completed in {end_time:.2f} seconds")
        self.logger.info(f"📸 Extracted {len(images)} images from {len(images)} found")
        self.logger.info(f"🔍 OCR extracted text from {images_with_text} images using EasyOCR")
        
        return results
    
    def parse_handwritten_document(self, input_path: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        Parse handwritten document by extracting images first, then processing with LLMWhisperer.
        
        Args:
            input_path: Path to the input document
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing parsing results and metadata
        """
        if not self.llmwhisperer_client:
            raise ValueError("LLMWhisperer client not initialized. Please provide API key.")
        
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        self.logger.info(f"🚀 Starting handwritten document processing: {input_path}")
        start_time = time.time()
        
        # Check if it's a document with images that need extraction
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        if input_path.suffix.lower() in image_extensions:
            # Process standalone image directly
            images = self._process_standalone_image(input_path, output_dir)
            doc_filename = input_path.stem
        else:
            # Extract images from document first
            converter = self._create_converter()
            conv_result = converter.convert(input_path)
            doc = conv_result.document
            doc_filename = input_path.stem
            
            # Extract images from document
            images = self._extract_images_from_document(doc, output_dir, doc_filename)
        
        if not images:
            self.logger.error(f"❌ No images found in {input_path}")
            return {
                'input_file': str(input_path),
                'output_directory': str(output_dir),
                'processing_time': time.time() - start_time,
                'status': 'error',
                'error': 'No images found to process'
            }
        
        # Process each extracted image with LLMWhisperer
        llmwhisperer_results = []
        total_text_length = 0
        
        for i, image_info in enumerate(images):
            if image_info['filepath']:
                image_path = Path(image_info['filepath'])
                
                if image_path.exists():
                    self.logger.info(f"🔍 Processing image {i+1}/{len(images)} with LLMWhisperer: {image_path.name}")
                    
                    # Convert image to standard format if needed
                    try:
                        with Image.open(image_path) as img:
                            # Convert to RGB if needed
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            
                            # Save as JPEG for better compatibility
                            jpeg_path = image_path.with_suffix('.jpg')
                            img.save(jpeg_path, 'JPEG', quality=95)
                            
                            # Process the converted image with LLMWhisperer
                            result = self.llmwhisperer_client.extract_text(jpeg_path)
                            
                            # Clean up temporary file
                            jpeg_path.unlink()
                    except Exception as e:
                        self.logger.error(f"❌ Error converting image {image_path}: {e}")
                        # Fallback to original image
                        result = self.llmwhisperer_client.extract_text(image_path)
                    
                    # Add image info to result
                    result['image_info'] = image_info
                    result['image_index'] = i
                    
                    llmwhisperer_results.append(result)
                    
                    if result.get('status') == 'success':
                        text_length = result.get('text_length', 0)
                        total_text_length += text_length
                        self.logger.info(f"✅ Image {i+1}: {text_length} characters extracted")
                    else:
                        self.logger.error(f"❌ Image {i+1}: {result.get('error', 'Unknown error')}")
                else:
                    self.logger.error(f"❌ Image file not found: {image_path}")
        
        end_time = time.time() - start_time
        
        # Create CSV from LLMWhisperer results
        self._create_csv_from_llmwhisperer_results(llmwhisperer_results, output_dir, doc_filename)
        
        # Calculate statistics
        successful_results = [r for r in llmwhisperer_results if r.get('status') == 'success']
        
        # Prepare results
        results = {
            'input_file': str(input_path),
            'output_directory': str(output_dir),
            'processing_time': end_time,
            'status': 'success' if successful_results else 'error',
            'total_images_found': len(images),
            'images_processed': len(llmwhisperer_results),
            'images_successful': len(successful_results),
            'total_text_length': total_text_length,
            'llmwhisperer_results': llmwhisperer_results
        }
        
        if successful_results:
            self.logger.info(f"✅ Handwritten document processing completed in {end_time:.2f} seconds")
            self.logger.info(f"📸 Processed {len(images)} images, {len(successful_results)} successful")
            self.logger.info(f"📝 Total text extracted: {total_text_length} characters")
        else:
            self.logger.error(f"❌ Handwritten document processing failed: No successful extractions")
        
        return results


def get_supported_files(documents_dir: Path) -> List[Path]:
    """
    Get all supported files from the documents directory.
    
    Args:
        documents_dir: Path to documents directory
        
    Returns:
        List of supported file paths
    """
    supported_extensions = {
        # Documents
        '.pdf', '.docx', '.doc',
        # Images
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'
    }
    
    files = []
    for ext in supported_extensions:
        files.extend(documents_dir.glob(f"*{ext}"))
        files.extend(documents_dir.glob(f"*{ext.upper()}"))
    
    return sorted(files)


def get_handwritten_files(handwritten_dir: Path) -> List[Path]:
    """
    Get all supported files from the handwritten documents directory.
    
    Args:
        handwritten_dir: Path to handwritten documents directory
        
    Returns:
        List of supported file paths
    """
    supported_extensions = {
        # Documents
        '.pdf', '.docx', '.doc',
        # Images
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'
    }
    
    files = []
    for ext in supported_extensions:
        files.extend(handwritten_dir.glob(f"*{ext}"))
        files.extend(handwritten_dir.glob(f"*{ext.upper()}"))
    
    return sorted(files)


def ask_confirmation(files: List[Path], file_type: str = "files") -> bool:
    """
    Ask user for confirmation before processing files.
    
    Args:
        files: List of files to process
        file_type: Type of files being processed
        
    Returns:
        True if user confirms, False otherwise
    """
    print(f"\n📁 Found {len(files)} {file_type} to process:")
    for i, file in enumerate(files, 1):
        print(f"   {i}. {file.name}")
    
    while True:
        response = input(f"\n❓ Do you want to process these {len(files)} {file_type}? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")


def get_llmwhisperer_api_key() -> Optional[str]:
    """
    Get LLMWhisperer API key from environment variable.
    
    Returns:
        API key if available, None otherwise
    """
    # Load environment variables from .env file
    load_dotenv()
    
    api_key = os.getenv('LLMWHISPERER_API_KEY')
    
    if not api_key:
        print("\nℹ️  LLMWhisperer API key not found in environment.")
        print("   Set LLMWHISPERER_API_KEY environment variable or add to .env file to process handwritten documents.")
        return None
    
    return api_key


def main():
    """Main function to process documents and images."""
    print("📄 Document Image Extraction and OCR")
    print("=" * 50)
    print("Extracts images and performs OCR using EasyOCR")
    print("Supports: PDF, Word documents, standalone images, and handwritten documents")
    print("=" * 50)
    
    # Get LLMWhisperer API key from environment
    llmwhisperer_api_key = get_llmwhisperer_api_key()
    
    # Initialize parser
    parser = DocumentImageOCRParser(llmwhisperer_api_key)
    
    # Process regular documents
    documents_dir = Path("documents")
    if documents_dir.exists():
        files = get_supported_files(documents_dir)
        
        if files:
            # Ask for confirmation
            if ask_confirmation(files, "regular files"):
                # Ask user which OCR method to use
                print(f"\n🤖 Choose OCR method for regular documents:")
                print("   1. EasyOCR (faster, good for printed text)")
                print("   2. LLMWhisperer (better for complex/handwritten text)")
                
                while True:
                    choice = input("   Enter your choice (1 or 2): ").strip()
                    if choice in ['1', '2']:
                        break
                    print("   ❌ Invalid choice. Please enter 1 or 2.")
                
                use_llmwhisperer = choice == '2'
                
                if use_llmwhisperer and not llmwhisperer_api_key:
                    print("   ❌ LLMWhisperer API key not found. Falling back to EasyOCR.")
                    use_llmwhisperer = False
                
                print(f"\n🚀 Starting regular document processing with {'LLMWhisperer' if use_llmwhisperer else 'EasyOCR'}...")
                
                # Process each file
                for i, file in enumerate(files, 1):
                    print(f"\n🔍 Processing file {i}/{len(files)}: {file.name}")
                    print("-" * 50)
                    
                    try:
                        if use_llmwhisperer:
                            result = parser.parse_handwritten_document(str(file), "output")
                        else:
                            result = parser.parse_document(str(file), "output")
                        
                        print(f"✅ Completed: {file.name}")
                        
                        if use_llmwhisperer:
                            print(f"   📝 Status: {result['status']}")
                            print(f"   📸 Images found: {result.get('total_images_found', 0)}")
                            print(f"   🔍 Images processed: {result.get('images_processed', 0)}")
                            print(f"   ✅ Images successful: {result.get('images_successful', 0)}")
                            print(f"   📄 Total text length: {result.get('total_text_length', 0)} characters")
                            print(f"   ⏱️  Processing time: {result['processing_time']:.2f}s")
                            
                            if result['status'] == 'success':
                                print(f"   🎉 Successfully extracted text using LLMWhisperer!")
                                
                                # Show sample text from first successful result
                                llmwhisperer_results = result.get('llmwhisperer_results', [])
                                if llmwhisperer_results:
                                    first_success = next((r for r in llmwhisperer_results if r.get('status') == 'success'), None)
                                    if first_success:
                                        extracted_text = first_success.get('extracted_text', '')
                                        if extracted_text:
                                            sample_text = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
                                            print(f"   📄 Sample text: {sample_text}")
                                
                                # Show output files created
                                output_dir = Path(result['output_directory'])
                                csv_file = output_dir / f"{file.stem}-llmwhisperer-results.csv"
                                txt_file = output_dir / f"{file.stem}-llmwhisperer-results.txt"
                                
                                print(f"   📁 Output files created:")
                                print(f"      📊 CSV results: {csv_file}")
                                print(f"      📝 Text results: {txt_file}")
                            else:
                                print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")
                        else:
                            print(f"   📸 Images found: {result['total_images_found']}")
                            print(f"   💾 Images extracted: {result['images_extracted']}")
                            print(f"   🔍 Images with text: {result['images_with_text']}")
                            print(f"   📝 Total text length: {result['total_text_length']} characters")
                            print(f"   ⏱️  Processing time: {result['processing_time']:.2f}s")
                            
                            if result['images_with_text'] > 0:
                                print(f"   🎉 Successfully extracted text from {result['images_with_text']} images!")
                                
                                # Show sample text from first image
                                if result['ocr_results']:
                                    first_image = result['ocr_results'][0]
                                    if first_image.get('ocr_text'):
                                        sample_text = first_image['ocr_text'][:200] + "..." if len(first_image['ocr_text']) > 200 else first_image['ocr_text']
                                        print(f"   📄 Sample text from Image 1: {sample_text}")
                                
                                # Show output files created
                                output_dir = Path(result['output_directory'])
                                csv_file = output_dir / f"{file.stem}-ocr-results.csv"
                                txt_file = output_dir / f"{file.stem}-ocr-results.txt"
                                images_dir = output_dir / "extracted_images"
                                
                                print(f"   📁 Output files created:")
                                print(f"      📊 CSV results: {csv_file}")
                                print(f"      📝 Text results: {txt_file}")
                                if images_dir.exists():
                                    image_count = len(list(images_dir.glob('*')))
                                    print(f"      🖼️  Extracted images: {images_dir} ({image_count} files)")
                                
                            else:
                                print(f"   ⚠️  No text extracted from images")
                            
                    except Exception as e:
                        print(f"❌ Error processing {file.name}: {e}")
            else:
                print("❌ Regular document processing cancelled by user")
        else:
            print("ℹ️  No regular documents found")
    else:
        print("ℹ️  Documents directory not found")
    
    # Process handwritten documents
    handwritten_dir = Path("handwritten_documents")
    if handwritten_dir.exists():
        handwritten_files = get_handwritten_files(handwritten_dir)
        
        if handwritten_files:
            if llmwhisperer_api_key:
                # Ask for confirmation
                if ask_confirmation(handwritten_files, "handwritten documents"):
                    print(f"\n🚀 Starting handwritten document processing with LLMWhisperer...")
                    
                    # Process each file
                    for i, file in enumerate(handwritten_files, 1):
                        print(f"\n🔍 Processing handwritten document {i}/{len(handwritten_files)}: {file.name}")
                        print("-" * 50)
                        
                        try:
                            result = parser.parse_handwritten_document(str(file), "output")
                            
                            print(f"✅ Completed: {file.name}")
                            print(f"   📝 Status: {result['status']}")
                            print(f"   📸 Images found: {result.get('total_images_found', 0)}")
                            print(f"   🔍 Images processed: {result.get('images_processed', 0)}")
                            print(f"   ✅ Images successful: {result.get('images_successful', 0)}")
                            print(f"   📄 Total text length: {result.get('total_text_length', 0)} characters")
                            print(f"   ⏱️  Processing time: {result['processing_time']:.2f}s")
                            
                            if result['status'] == 'success':
                                print(f"   🎉 Successfully extracted text using LLMWhisperer!")
                                
                                # Show sample text from first successful result
                                llmwhisperer_results = result.get('llmwhisperer_results', [])
                                if llmwhisperer_results:
                                    first_success = next((r for r in llmwhisperer_results if r.get('status') == 'success'), None)
                                    if first_success:
                                        extracted_text = first_success.get('extracted_text', '')
                                        if extracted_text:
                                            sample_text = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
                                            print(f"   📄 Sample text: {sample_text}")
                                
                                # Show output files created
                                output_dir = Path(result['output_directory'])
                                csv_file = output_dir / f"{file.stem}-llmwhisperer-results.csv"
                                txt_file = output_dir / f"{file.stem}-llmwhisperer-results.txt"
                                
                                print(f"   📁 Output files created:")
                                print(f"      📊 CSV results: {csv_file}")
                                print(f"      📝 Text results: {txt_file}")
                                
                            else:
                                print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")
                                    
                        except Exception as e:
                            print(f"❌ Error processing {file.name}: {e}")
                else:
                    print("❌ Handwritten document processing cancelled by user")
            else:
                print(f"ℹ️  Found {len(handwritten_files)} handwritten documents but no API key available.")
                print("   Set LLMWHISPERER_API_KEY environment variable or add to .env file to process them.")
        else:
            print("ℹ️  No handwritten documents found")
    else:
        print("ℹ️  Handwritten documents directory not found")
    
    print(f"\n🎯 Processing Summary:")
    print("=" * 50)
    print(f"✅ Processing completed")
    print(f"📁 Results saved in 'output/' directory")
    print("=" * 50)


if __name__ == "__main__":
    main()
