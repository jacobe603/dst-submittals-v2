#!/usr/bin/env python3
"""
Gotenberg-based document converter for DST Submittals Generator V2

High-quality document conversion using Gotenberg API with built-in merging
and quality control for technical drawings.
"""

import os
import time
import subprocess
import requests
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Union
import json

# PDF bookmark support
try:
    from pypdf import PdfWriter, PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfWriter, PdfReader
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

try:
    from .logger import get_logger
    from .title_page_generator import TitlePageGenerator
except ImportError:
    from logger import get_logger
    from title_page_generator import TitlePageGenerator

logger = get_logger('gotenberg_converter')

class GotenbergConverter:
    """
    Document converter using Gotenberg API
    
    Provides high-quality document conversion with built-in merging,
    quality control, and support for technical drawings.
    """
    
    def __init__(self, gotenberg_url: str = 'http://localhost:3000'):
        self.base_url = gotenberg_url.rstrip('/')
        self.session = requests.Session()
        self.container_name = 'gotenberg-service'
        
        # Initialize ReportLab title page generator
        try:
            self.title_generator = TitlePageGenerator()
            self.reportlab_available = True
            logger.debug("ReportLab title page generator initialized")
        except ImportError:
            self.title_generator = None
            self.reportlab_available = False
            logger.warning("ReportLab not available, falling back to HTML title pages")
        
        # Quality presets for different use cases
        # Note: maxImageResolution must be 75, 150, 300, 600, or 1200 (Gotenberg requirement)
        self.quality_presets = {
            'fast': {
                'quality': '80',
                'maxImageResolution': '150',
                'losslessImageCompression': 'false',
                'reduceImageResolution': 'true'
            },
            'balanced': {
                'quality': '90',
                'maxImageResolution': '300',
                'losslessImageCompression': 'false',
                'reduceImageResolution': 'false'
            },
            'high': {
                'quality': '100',
                'maxImageResolution': '600',
                'losslessImageCompression': 'true',
                'reduceImageResolution': 'false'
            },
            'maximum': {
                'quality': '100',
                'maxImageResolution': '1200',
                'losslessImageCompression': 'true',
                'reduceImageResolution': 'false'
            }
        }
        
        # Ensure Gotenberg is running
        self.ensure_service_running()
    
    def check_service_health(self) -> bool:
        """Check if Gotenberg service is healthy"""
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    def check_docker_running(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def start_gotenberg_container(self) -> bool:
        """Start Gotenberg Docker container"""
        if not self.check_docker_running():
            logger.error("Docker is not available. Please install Docker first.")
            return False
        
        try:
            # Check if container already exists
            check_cmd = ['docker', 'ps', '-a', '--filter', f'name={self.container_name}', '--format', '{{.Names}}']
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if self.container_name in result.stdout:
                # Container exists, start it
                logger.info(f"Starting existing {self.container_name} container...")
                subprocess.run(['docker', 'start', self.container_name], check=True)
            else:
                # Create and start new container
                logger.info("Creating new Gotenberg container...")
                subprocess.run([
                    'docker', 'run', '-d',
                    '--name', self.container_name,
                    '-p', '3000:3000',
                    '--restart', 'unless-stopped',
                    'gotenberg/gotenberg:8'
                ], check=True)
            
            # Wait for service to be ready
            for i in range(30):  # Wait up to 30 seconds
                if self.check_service_health():
                    logger.info("Gotenberg service is ready")
                    return True
                time.sleep(1)
            
            logger.error("Gotenberg service failed to start within 30 seconds")
            return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Gotenberg container: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error starting Gotenberg: {e}")
            return False
    
    def ensure_service_running(self) -> bool:
        """Ensure Gotenberg service is running and healthy"""
        if self.check_service_health():
            logger.debug("Gotenberg service is already running")
            return True
        
        logger.info("Gotenberg service not found, attempting to start...")
        return self.start_gotenberg_container()
    
    def create_title_page_html(self, equipment_tag: str, documents: List[str] = None) -> str:
        """
        Create simple HTML title page for equipment group
        Just large bold text in center of letter-size page
        
        Args:
            equipment_tag: Equipment identifier (e.g., "AHU-1", "CUT SHEETS")
            documents: Unused (kept for compatibility)
        
        Returns:
            HTML content for title page
        """
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: 8.5in 11in;
                    margin: 0;
                }}
                body {{
                    font-family: 'Helvetica', Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    width: 8.5in;
                    height: 11in;
                    -webkit-print-color-adjust: exact;
                }}
                .title-container {{
                    text-align: center;
                    width: 100%;
                    padding-top: 4.5in;  /* Center on 11in page (approximately) */
                }}
                h1 {{
                    font-size: 72px;
                    font-weight: bold;
                    color: #000000;
                    margin: 0;
                    padding: 0;
                }}
            </style>
        </head>
        <body>
            <div class="title-container">
                <h1>{equipment_tag.replace('CUTSHEETS', 'CUT SHEETS')}</h1>
            </div>
        </body>
        </html>
        """
        return html_content
    
    def convert_files_to_pdf(self, 
                           file_paths: List[str], 
                           output_path: str,
                           quality_mode: str = 'high',
                           equipment_tag: str = None,
                           include_title_page: bool = True) -> bool:
        """
        Convert multiple files to single PDF by converting each individually then merging
        This ensures correct page order by avoiding LibreOffice's internal ordering
        
        Args:
            file_paths: List of file paths to convert
            output_path: Output PDF file path
            quality_mode: Quality preset (fast/balanced/high/maximum)
            equipment_tag: Equipment identifier for title page
            include_title_page: Whether to include title page
        
        Returns:
            True if conversion successful, False otherwise
        """
        if not self.ensure_service_running():
            logger.error(
                f"Gotenberg service is not available\n"
                f"URL: {self.base_url}\n"
                f"Docker running: {self.check_docker_running()}\n"
                f"Container name: {self.container_name}\n"
                f"Try running: docker start {self.container_name}"
            )
            return False
        
        if not file_paths:
            logger.error(
                f"No files provided for conversion\n"
                f"Equipment tag: {equipment_tag or 'None'}\n"
                f"Quality mode: {quality_mode}"
            )
            return False
        
        try:
            individual_pdfs = []
            
            # Create title page PDF first
            if include_title_page and equipment_tag:
                title_pdf = tempfile.mktemp(suffix='_title.pdf')
                
                # Use ReportLab if available, otherwise fall back to HTML
                if self.reportlab_available:
                    try:
                        self.title_generator.create_title_page_pdf(equipment_tag, title_pdf)
                        individual_pdfs.append(title_pdf)
                        logger.info(f"Created ReportLab title page PDF for {equipment_tag}")
                    except Exception as e:
                        logger.warning(f"ReportLab title page failed, falling back to HTML: {e}")
                        if self._convert_single_file_to_pdf(None, title_pdf, equipment_tag, quality_mode, is_title=True):
                            individual_pdfs.append(title_pdf)
                            logger.info(f"Created HTML title page PDF for {equipment_tag}")
                else:
                    # Fall back to HTML method
                    if self._convert_single_file_to_pdf(None, title_pdf, equipment_tag, quality_mode, is_title=True):
                        individual_pdfs.append(title_pdf)
                        logger.info(f"Created HTML title page PDF for {equipment_tag}")
            
            # Convert each file individually to maintain order
            logger.info(f"Converting {len(file_paths)} files individually to maintain order:")
            for i, file_path in enumerate(file_paths):
                if not os.path.exists(file_path):
                    parent_dir = os.path.dirname(file_path)
                    available_files = []
                    if os.path.exists(parent_dir):
                        available_files = os.listdir(parent_dir)[:5]
                    logger.warning(
                        f"File not found: {file_path}\n"
                        f"Parent directory: {parent_dir}\n"
                        f"Parent exists: {os.path.exists(parent_dir)}\n"
                        f"Available files: {available_files}"
                    )
                    continue
                
                filename = os.path.basename(file_path)
                logger.info(f"  Converting {i+1}/{len(file_paths)}: {filename}")
                
                temp_pdf = tempfile.mktemp(suffix=f'_{i}_{filename}.pdf')
                if self._convert_single_file_to_pdf(file_path, temp_pdf, equipment_tag, quality_mode):
                    individual_pdfs.append(temp_pdf)
                else:
                    logger.warning(f"Failed to convert {filename}")
            
            if not individual_pdfs:
                logger.error("No files were successfully converted")
                return False
            
            # Merge all individual PDFs in correct order
            logger.info(f"Merging {len(individual_pdfs)} PDFs in correct order...")
            success = self.merge_pdfs(individual_pdfs, output_path)
            
            # Count pages in final PDF for bookmark calculation
            page_count = 0
            if success and os.path.exists(output_path):
                page_count = self._count_pdf_pages(output_path)
            
            # Cleanup individual PDFs
            for pdf_path in individual_pdfs:
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp PDF {pdf_path}: {e}")
            
            return {
                'success': success,
                'page_count': page_count,
                'title_page_included': include_title_page and equipment_tag is not None
            }
        
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return False
    
    def _convert_single_file_to_pdf(self, file_path: str, output_path: str, 
                                   equipment_tag: str, quality_mode: str, 
                                   is_title: bool = False) -> bool:
        """
        Convert a single file to PDF using Gotenberg
        
        Args:
            file_path: Path to file to convert (None for title page)
            output_path: Output PDF path
            equipment_tag: Equipment tag for title page
            quality_mode: Quality preset
            is_title: Whether this is a title page conversion
        
        Returns:
            True if successful, False otherwise
        """
        try:
            files = []
            
            if is_title:
                # Create title page
                title_html = self.create_title_page_html(equipment_tag)
                files.append(('files', ('title.html', title_html, 'text/html')))
            else:
                # Add single document file
                filename = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    files.append(('files', (filename, file_content)))
            
            # Get quality settings
            quality_settings = self.quality_presets.get(quality_mode, self.quality_presets['high'])
            
            # Prepare form data - NO merge since it's a single file
            data = {
                'pdfa': 'PDF/A-2b',  # Archival quality
                **quality_settings
            }
            
            # Make conversion request
            response = self.session.post(
                f'{self.base_url}/forms/libreoffice/convert',
                files=files,
                data=data,
                timeout=300  # 5 minutes timeout
            )
            
            if response.status_code == 200:
                # Save the PDF
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                logger.error(f"Single file conversion failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Single file conversion error: {e}")
            return False
    
    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> bool:
        """
        Merge multiple PDF files into one
        Gotenberg sorts files alphabetically by filename, so we use ordered filenames
        
        Args:
            pdf_paths: List of PDF file paths to merge (in desired order)
            output_path: Output merged PDF path
        
        Returns:
            True if merge successful, False otherwise
        """
        if not self.ensure_service_running():
            logger.error(
                f"Gotenberg service is not available\n"
                f"URL: {self.base_url}\n"
                f"Docker running: {self.check_docker_running()}\n"
                f"Container name: {self.container_name}\n"
                f"Try running: docker start {self.container_name}"
            )
            return False
        
        if not pdf_paths:
            logger.error(
                f"No PDFs provided for merging\n"
                f"Output path: {output_path}\n"
                f"Service available: {self.check_service_health()}"
            )
            return False
        
        try:
            files = []
            logger.info(f"PDF merge order (using alphabetical filenames for Gotenberg):")
            for i, pdf_path in enumerate(pdf_paths):
                if not os.path.exists(pdf_path):
                    logger.warning(f"PDF not found: {pdf_path}")
                    continue
                
                # Create ordered filename that will sort correctly alphabetically
                # Format: 001_filename.pdf, 002_filename.pdf, etc.
                original_filename = os.path.basename(pdf_path)
                ordered_filename = f"{i+1:03d}_{original_filename}"
                
                logger.info(f"  Position {i+1}: {original_filename} -> {ordered_filename}")
                
                with open(pdf_path, 'rb') as f:
                    file_content = f.read()
                    files.append(('files', (ordered_filename, file_content, 'application/pdf')))
            
            if not files:
                logger.error("No valid PDFs to merge")
                return False
            
            logger.info(f"Merging {len(files)} PDF files...")
            
            # Make merge request
            response = self.session.post(
                f'{self.base_url}/forms/pdfengines/merge',
                files=files,
                timeout=120  # 2 minutes timeout
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                logger.info(f"Merge successful: {output_path} ({file_size:,} bytes)")
                return True
            else:
                logger.error(f"Merge failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Merge error: {e}")
            return False
    
    def add_bookmarks_to_pdf(self, pdf_path: str, equipment_page_positions: Dict[str, int], processing_order: List[str]) -> bool:
        """
        Add PDF bookmarks/outline with equipment tags as parents and document types as children
        
        Args:
            pdf_path: Path to the PDF file to add bookmarks to
            equipment_page_positions: Dict mapping equipment tag to calculated page number (0-indexed)
            processing_order: Order of equipment tags
        
        Returns:
            True if bookmarks added successfully, False otherwise
        """
        if not PYPDF_AVAILABLE:
            logger.warning("pypdf not available, skipping bookmark creation")
            return False
        
        if not os.path.exists(pdf_path):
            parent_dir = os.path.dirname(pdf_path)
            available_files = []
            if os.path.exists(parent_dir):
                available_files = [f for f in os.listdir(parent_dir) if f.endswith('.pdf')][:5]
            logger.error(
                f"PDF file not found: {pdf_path}\n"
                f"Parent directory: {parent_dir}\n"
                f"Parent exists: {os.path.exists(parent_dir)}\n"
                f"Available PDFs: {available_files}"
            )
            return False
        
        try:
            # Read the existing PDF
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                writer = PdfWriter()
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                logger.info(f"Using calculated page positions for bookmarks (deterministic method)")
                
                # Use the calculated page positions (NO heuristics or scanning)
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} total pages")
                
                # Create bookmarks using calculated page positions (deterministic)
                logger.info(f"Creating bookmarks for {len(equipment_page_positions)} equipment groups...")
                
                for equipment_tag in processing_order:
                    if equipment_tag in equipment_page_positions:
                        calculated_page = equipment_page_positions[equipment_tag]
                        
                        # Verify page number is within PDF bounds
                        if calculated_page < total_pages:
                            # Display name (convert CUTSHEETS to CUT SHEETS for display)
                            display_name = equipment_tag.replace('CUTSHEETS', 'CUT SHEETS')
                            writer.add_outline_item(display_name, calculated_page)
                            logger.info(f"Added bookmark: '{display_name}' at calculated page {calculated_page + 1}")
                        else:
                            logger.warning(f"Calculated page {calculated_page + 1} for {equipment_tag} exceeds PDF page count ({total_pages})")
                    else:
                        logger.warning(f"No calculated page position for {equipment_tag}")
                
                # Write the updated PDF with bookmarks
                temp_path = pdf_path + '.tmp'
                with open(temp_path, 'wb') as output_file:
                    writer.write(output_file)
                
                # Replace original file
                os.replace(temp_path, pdf_path)
                
                logger.info(f"Successfully added bookmarks to {pdf_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add bookmarks: {e}")
            return False
    
    def _count_pdf_pages(self, pdf_path: str) -> int:
        """
        Count pages in a PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Number of pages in the PDF
        """
        if not PYPDF_AVAILABLE:
            logger.warning("pypdf not available, assuming 1 page")
            return 1
            
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                page_count = len(reader.pages)
                logger.debug(f"PDF {os.path.basename(pdf_path)} has {page_count} pages")
                return page_count
        except Exception as e:
            logger.warning(f"Could not count pages in {pdf_path}: {e}")
            return 1  # Fallback assumption
    
    def get_service_info(self) -> Dict:
        """Get information about Gotenberg service"""
        try:
            health_response = self.session.get(f'{self.base_url}/health', timeout=5)
            
            return {
                'status': 'healthy' if health_response.status_code == 200 else 'unhealthy',
                'url': self.base_url,
                'container_name': self.container_name,
                'docker_available': self.check_docker_running(),
                'quality_presets': list(self.quality_presets.keys()),
                'title_page_generator': {
                    'reportlab_available': self.reportlab_available,
                    'method': 'ReportLab' if self.reportlab_available else 'HTML fallback'
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'url': self.base_url,
                'title_page_generator': {
                    'reportlab_available': self.reportlab_available,
                    'method': 'ReportLab' if self.reportlab_available else 'HTML fallback'
                }
            }


def test_gotenberg_converter():
    """Test function for Gotenberg converter"""
    converter = GotenbergConverter()
    
    # Test service health
    info = converter.get_service_info()
    print(f"Gotenberg service info: {json.dumps(info, indent=2)}")
    
    if info['status'] != 'healthy':
        print("Service not healthy, attempting to start...")
        if not converter.ensure_service_running():
            print("Failed to start Gotenberg service")
            return False
    
    print("Gotenberg converter is ready!")
    return True


if __name__ == '__main__':
    test_gotenberg_converter()