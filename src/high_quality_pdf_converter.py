#!/usr/bin/env python3
"""
High-quality document to PDF converter for CS Air Handler documents
Supports both .doc and .docx files with multiple conversion methods
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Dict
import json
from docx2pdf import convert as docx2pdf_convert
import pypdf
from pypdf import PdfReader, PdfWriter
import re
try:
    import win32com.client
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

class DocumentPDFConverter:
    def __init__(self, docs_path: str, output_dir: str = "converted_pdfs"):
        self.docs_path = docs_path
        self.output_dir = output_dir
        self.conversion_log = []
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
    def log_conversion(self, filename: str, method: str, success: bool, output_path: str = None, error: str = None):
        """Log conversion attempts"""
        log_entry = {
            'filename': filename,
            'method': method,
            'success': success,
            'output_path': output_path,
            'error': error
        }
        self.conversion_log.append(log_entry)
        
    def check_libreoffice_available(self) -> bool:
        """Check if LibreOffice is available"""
        try:
            # Try different LibreOffice command names
            commands = ['soffice', 'libreoffice', 'libreoffice.exe', 'soffice.exe']
            for cmd in commands:
                if shutil.which(cmd):
                    return True
            return False
        except Exception:
            return False
    
    def convert_with_libreoffice(self, input_path: str, output_dir: str) -> Optional[str]:
        """Convert document using LibreOffice headless mode"""
        try:
            filename = os.path.basename(input_path)
            print(f"  [LibreOffice] Converting {filename}...")
            
            # Try different LibreOffice commands
            commands = ['soffice', 'libreoffice', 'libreoffice.exe', 'soffice.exe']
            
            for cmd in commands:
                if shutil.which(cmd):
                    # Run LibreOffice conversion
                    result = subprocess.run([
                        cmd, '--headless', '--convert-to', 'pdf',
                        '--outdir', output_dir, input_path
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        # Determine output file path
                        base_name = os.path.splitext(filename)[0]
                        output_path = os.path.join(output_dir, f"{base_name}.pdf")
                        
                        if os.path.exists(output_path):
                            self.log_conversion(filename, 'libreoffice', True, output_path)
                            return output_path
                    
                    break
            
            self.log_conversion(filename, 'libreoffice', False, error="LibreOffice conversion failed")
            return None
            
        except subprocess.TimeoutExpired:
            self.log_conversion(filename, 'libreoffice', False, error="Conversion timeout")
            return None
        except Exception as e:
            self.log_conversion(filename, 'libreoffice', False, error=str(e))
            return None
    
    def convert_with_docx2pdf(self, input_path: str, output_dir: str) -> Optional[str]:
        """Convert document using docx2pdf (Windows only, requires MS Office)"""
        try:
            filename = os.path.basename(input_path)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base_name}.pdf")
            
            print(f"  [docx2pdf] Converting {filename}...")
            
            # docx2pdf requires the output path
            docx2pdf_convert(input_path, output_path)
            
            if os.path.exists(output_path):
                self.log_conversion(filename, 'docx2pdf', True, output_path)
                return output_path
            else:
                self.log_conversion(filename, 'docx2pdf', False, error="Output file not created")
                return None
                
        except Exception as e:
            self.log_conversion(filename, 'docx2pdf', False, error=str(e))
            return None

    def convert_with_word_com(self, input_path: str, output_dir: str) -> Optional[str]:
        """Convert document using Microsoft Word COM automation"""
        if not WORD_AVAILABLE:
            return None
            
        try:
            filename = os.path.basename(input_path)
            base_name = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{base_name}.pdf")
            
            print(f"  [Word COM] Converting {filename}...")
            
            # Convert to absolute paths
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            
            # Create Word application
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False  # Keep Word hidden
            
            try:
                # Open document
                doc = word.Documents.Open(input_path, ReadOnly=True)
                
                # Export as PDF
                # wdExportFormatPDF = 17
                doc.ExportAsFixedFormat(
                    OutputFileName=output_path,
                    ExportFormat=17,  # PDF format
                    OpenAfterExport=False,
                    OptimizeFor=1,  # wdExportOptimizeForPrint = 1 (for quality)
                    BitmapMissingFonts=True,
                    DocStructureTags=False,
                    CreateBookmarks=False
                )
                
                # Close document
                doc.Close()
                
            finally:
                # Always quit Word
                word.Quit()
            
            if os.path.exists(output_path):
                self.log_conversion(filename, 'word_com', True, output_path)
                return output_path
            else:
                self.log_conversion(filename, 'word_com', False, error="Output file not created")
                return None
                
        except Exception as e:
            # Make sure to quit Word if something went wrong
            try:
                word.Quit()
            except:
                pass
            self.log_conversion(filename, 'word_com', False, error=str(e))
            return None
    
    def convert_document_to_pdf(self, input_path: str) -> Optional[str]:
        """Convert a single document to PDF using the best available method"""
        filename = os.path.basename(input_path)
        print(f"\nConverting: {filename}")
        
        if input_path.endswith('.docx'):
            # For .docx files, try docx2pdf first (faster)
            pdf_path = self.convert_with_docx2pdf(input_path, self.output_dir)
            if pdf_path:
                return pdf_path
            
            # Try Word COM as fallback for .docx
            if WORD_AVAILABLE:
                pdf_path = self.convert_with_word_com(input_path, self.output_dir)
                if pdf_path:
                    return pdf_path
        
        elif input_path.endswith('.doc'):
            # For .doc files, try Word COM first (best quality)
            if WORD_AVAILABLE:
                pdf_path = self.convert_with_word_com(input_path, self.output_dir)
                if pdf_path:
                    return pdf_path
            
            # Try LibreOffice as fallback for .doc
            if self.check_libreoffice_available():
                pdf_path = self.convert_with_libreoffice(input_path, self.output_dir)
                if pdf_path:
                    return pdf_path
        
        print(f"  [FAILED] Could not convert {filename}")
        return None
    
    def has_dollar_sign(self, pdf_path: str) -> List[int]:
        """Check which pages contain dollar signs and return page numbers"""
        try:
            reader = PdfReader(pdf_path)
            pages_with_dollar = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    # Only flag pages that contain pricing information
                    # Look for $ followed by numbers (actual prices)
                    import re
                    price_pattern = r'\$\s*[\d,]+\.?\d*'
                    if re.search(price_pattern, text):
                        pages_with_dollar.append(page_num)
                        print(f"    Found pricing on page {page_num + 1}")
                except Exception:
                    # If we can't extract text, assume page is OK
                    continue
            
            return pages_with_dollar
        except Exception as e:
            print(f"  [WARNING] Could not check for dollar signs in {pdf_path}: {e}")
            return []
    
    def filter_pages_with_dollar(self, pdf_path: str) -> Optional[str]:
        """Remove pages containing dollar signs from PDF"""
        try:
            pages_with_dollar = self.has_dollar_sign(pdf_path)
            
            if not pages_with_dollar:
                print(f"  [OK] No pricing pages found")
                return pdf_path
            
            print(f"  [FILTER] Removing {len(pages_with_dollar)} pages with pricing info")
            
            # Create filtered PDF
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            total_pages = len(reader.pages)
            for page_num in range(total_pages):
                if page_num not in pages_with_dollar:
                    writer.add_page(reader.pages[page_num])
            
            # Save filtered PDF
            filtered_path = pdf_path.replace('.pdf', '_filtered.pdf')
            with open(filtered_path, 'wb') as output_file:
                writer.write(output_file)
            
            print(f"  [FILTERED] Saved to {os.path.basename(filtered_path)}")
            return filtered_path
            
        except Exception as e:
            print(f"  [WARNING] Could not filter pages: {e}")
            return pdf_path  # Return original if filtering fails
    
    def convert_all_documents(self, tag_mapping: Dict[str, str]) -> Dict[str, str]:
        """Convert all documents to PDF and return filename -> PDF path mapping"""
        print("="*60)
        print("CONVERTING DOCUMENTS TO HIGH-QUALITY PDF")
        print("="*60)
        
        pdf_mapping = {}
        
        for filename, tag in tag_mapping.items():
            if filename.endswith(('.doc', '.docx')):
                # Skip Item Summary files entirely as they contain pricing
                if 'Item Summary' in filename:
                    print(f"  [SKIP] {filename} - contains pricing information")
                    continue
                    
                input_path = os.path.join(self.docs_path, filename)
                
                if os.path.exists(input_path):
                    # Convert to PDF
                    pdf_path = self.convert_document_to_pdf(input_path)
                    
                    if pdf_path:
                        # Filter out pages with dollar signs
                        filtered_pdf_path = self.filter_pages_with_dollar(pdf_path)
                        pdf_mapping[filename] = filtered_pdf_path
                        print(f"  [SUCCESS] {filename} -> {os.path.basename(filtered_pdf_path)}")
                    else:
                        print(f"  [FAILED] Could not convert {filename}")
                else:
                    print(f"  [ERROR] File not found: {filename}")
        
        return pdf_mapping
    
    def print_conversion_summary(self):
        """Print conversion summary"""
        print("\n" + "="*60)
        print("CONVERSION SUMMARY")
        print("="*60)
        
        successful = [log for log in self.conversion_log if log['success']]
        failed = [log for log in self.conversion_log if not log['success']]
        
        print(f"Total conversions attempted: {len(self.conversion_log)}")
        print(f"Successful conversions: {len(successful)}")
        print(f"Failed conversions: {len(failed)}")
        
        # Group by method
        methods = {}
        for log in successful:
            method = log['method']
            methods[method] = methods.get(method, 0) + 1
        
        print("\nSuccessful conversions by method:")
        for method, count in methods.items():
            print(f"  {method}: {count}")
        
        if failed:
            print("\nFailed conversions:")
            for log in failed:
                print(f"  {log['filename']}: {log['error']}")

def main():
    """Main function to test the converter"""
    docs_path = r"C:\Users\jacob\Claude\python-docx\documents\CS_Air_Handler_Light_Kit"
    
    # Load tag mapping
    with open('tag_mapping_enhanced.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    tag_mapping = data['tag_mapping']
    
    # Create converter
    converter = DocumentPDFConverter(docs_path)
    
    # Convert all documents
    pdf_mapping = converter.convert_all_documents(tag_mapping)
    
    # Save PDF mapping
    with open('pdf_conversion_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(pdf_mapping, f, indent=2, ensure_ascii=False)
    
    # Print summary
    converter.print_conversion_summary()
    
    print(f"\nPDF mapping saved to: pdf_conversion_mapping.json")
    print(f"Converted PDFs saved to: {converter.output_dir}/")
    
    return converter

if __name__ == "__main__":
    converter = main()