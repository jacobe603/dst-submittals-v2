#!/usr/bin/env python3
"""
Create the final PDF from JSON structure with dynamic title page generation
"""

import os
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from pypdf import PdfReader, PdfWriter
try:
    from .title_page_generator import TitlePageGenerator
    from .config import get_config
    from .logger import get_logger, log_processing_stage, log_json_snapshot, log_file_conversion
except ImportError:
    # Handle case when running as standalone script
    from title_page_generator import TitlePageGenerator
    from config import get_config
    from logger import get_logger, log_processing_stage, log_json_snapshot, log_file_conversion

class FinalPDFAssembler:
    def __init__(self, docs_path: str, converted_pdfs_dir: str = None, 
                 title_pages_dir: str = None):
        self.config = get_config()
        self.docs_path = docs_path
        self.converted_pdfs_dir = converted_pdfs_dir or self.config.converted_pdfs_dir
        self.title_pages_dir = title_pages_dir or self.config.title_pages_dir
        self.logger = get_logger('pdf_assembler')
        
        # Ensure title pages directory exists
        os.makedirs(self.title_pages_dir, exist_ok=True)
        
        self.load_pdf_structure()
        
    def load_pdf_structure(self):
        """Load PDF structure from JSON file"""
        try:
            with open(self.config.tag_mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Use new PDF structure if available
            if 'pdf_structure' in data:
                self.pdf_structure = data['pdf_structure']
                self.metadata = data.get('metadata', {})
                self.logger.info(f"Loaded PDF structure with {len(self.pdf_structure)} items")
            else:
                # Fallback to legacy format
                self.logger.warning("Using legacy format - PDF structure not found")
                self.pdf_structure = self._convert_legacy_format(data)
                self.metadata = {'legacy_format': True}
                
            # Load PDF conversion mapping
            try:
                with open(self.config.pdf_conversion_mapping_file, 'r', encoding='utf-8') as f:
                    self.pdf_mapping = json.load(f)
            except FileNotFoundError:
                self.pdf_mapping = {}
                self.logger.warning(f"PDF conversion mapping not found: {self.config.pdf_conversion_mapping_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to load PDF structure: {e}")
            raise
    
    def _convert_legacy_format(self, data: Dict) -> List[Dict]:
        """Convert legacy tag_groups format to new PDF structure"""
        pdf_structure = []
        position = 1
        
        tag_groups = data.get('tag_groups', {})
        for tag in sorted(tag_groups.keys()):
            # Add title page
            pdf_structure.append({
                "type": "title_page",
                "tag": tag,
                "title": tag,
                "position": position,
                "include": True
            })
            position += 1
            
            # Add documents
            for filename in sorted(tag_groups[tag]):
                pdf_structure.append({
                    "type": "document",
                    "tag": tag,
                    "filename": filename,
                    "display_title": filename,
                    "file_type": "Unknown",
                    "converted_path": f"converted_pdfs/{os.path.splitext(filename)[0]}.pdf",
                    "position": position,
                    "include": True
                })
                position += 1
        
        return pdf_structure

    def generate_title_page(self, tag: str, title: str) -> str:
        """Generate a title page PDF for the given tag dynamically"""
        try:
            # Create safe filename from tag
            safe_tag = tag.replace('-', '_').replace(' ', '_')
            title_page_path = os.path.join(self.title_pages_dir, f"title_{safe_tag}.pdf")
            
            # Generate title page
            generator = TitlePageGenerator()
            generator.create_title_page(title, title_page_path)
            
            self.logger.info(f"Generated title page: {title_page_path}")
            return title_page_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate title page for {tag}: {e}")
            return None

    def add_pdf_to_writer(self, writer: PdfWriter, pdf_path: str, description: str = "", 
                          add_bookmark: bool = False, bookmark_title: str = None, 
                          bookmark_parent=None) -> tuple:
        """Add a PDF file to the writer, optionally add bookmark, return (success, start_page, end_page, bookmark_ref)"""
        try:
            if not os.path.exists(pdf_path):
                self.logger.warning(f"File not found: {pdf_path}")
                return False, None, None, None
            
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            
            # Record the starting page number (0-indexed)
            start_page = len(writer.pages)
            
            for page in reader.pages:
                writer.add_page(page)
            
            end_page = len(writer.pages) - 1
            
            # Add bookmark if requested
            bookmark_ref = None
            if add_bookmark and bookmark_title:
                bookmark_ref = writer.add_outline_item(
                    title=bookmark_title, 
                    page_number=start_page,
                    parent=bookmark_parent
                )
            
            self.logger.info(f"Added {os.path.basename(pdf_path)} ({page_count} pages)")
            return True, start_page, end_page, bookmark_ref
            
        except Exception as e:
            self.logger.error(f"Failed to add {pdf_path}: {e}")
            return False, None, None, None

    def resolve_converted_path(self, item: Dict) -> Optional[str]:
        """Resolve the actual converted PDF path for an item"""
        if item['type'] == 'cut_sheet':
            # Cut sheets are already PDFs, use the path directly
            return item.get('converted_path') or os.path.join(self.docs_path, item['filename'])
        
        # For documents, check multiple sources for the converted path
        filename = item.get('filename')
        if not filename:
            return None
            
        # 1. Try the converted_path from the item
        converted_path = item.get('converted_path')
        if converted_path and os.path.exists(converted_path):
            return converted_path
            
        # 2. Try the PDF mapping
        if filename in self.pdf_mapping:
            mapped_path = self.pdf_mapping[filename]
            if mapped_path and os.path.exists(mapped_path):
                return mapped_path
                
        # 3. Try default converted PDF directory
        base_name = os.path.splitext(filename)[0]
        default_path = os.path.join(self.converted_pdfs_dir, f"{base_name}.pdf")
        if os.path.exists(default_path):
            return default_path
            
        # 4. Try relative to docs path
        relative_path = os.path.join(self.docs_path, "converted_pdfs", f"{base_name}.pdf")
        if os.path.exists(relative_path):
            return relative_path
            
        self.logger.warning(f"Could not resolve converted path for {filename}")
        return None

    def create_final_pdf(self, output_filename: str = None) -> str:
        """Create the final PDF document from JSON structure"""
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"DST_Submittal_{timestamp}.pdf"
        
        # Log start of PDF assembly
        log_processing_stage('create_final_pdf', 'started', {
            'output_filename': output_filename,
            'structure_items': len(self.pdf_structure),
            'docs_path': self.docs_path
        })
        
        self.logger.info("="*70)
        self.logger.info("CREATING FINAL PDF FROM STRUCTURE")
        self.logger.info("="*70)
        
        writer = PdfWriter()
        
        # Filter to only included items, sorted by position
        included_items = [item for item in self.pdf_structure if item.get('include', True)]
        included_items.sort(key=lambda x: x.get('position', 0))
        
        self.logger.info(f"Processing {len(included_items)} included items from structure")
        
        # Log structure processing details
        log_processing_stage('pdf_assembly_items', 'started', {
            'total_items': len(self.pdf_structure),
            'included_items': len(included_items),
            'excluded_items': len(self.pdf_structure) - len(included_items)
        })
        
        # Track current parent bookmark for hierarchical organization
        current_parent_bookmark = None
        title_pages_added = 0
        documents_added = 0
        cut_sheets_added = 0
        failed_items = 0
        
        # Process each item in the structure
        for i, item in enumerate(included_items, 1):
            item_type = item.get('type')
            
            self.logger.info(f"Processing item {i}/{len(included_items)}: {item_type}")
            
            if item_type == 'title_page':
                # Generate title page dynamically
                tag = item.get('tag', '')
                title = item.get('title', tag)
                
                self.logger.info(f"Generating title page for: {title}")
                title_page_path = self.generate_title_page(tag, title)
                
                if title_page_path and os.path.exists(title_page_path):
                    success, start_page, end_page, bookmark_ref = self.add_pdf_to_writer(
                        writer, title_page_path, f"Title page for {title}",
                        add_bookmark=True, bookmark_title=title
                    )
                    
                    if success:
                        current_parent_bookmark = bookmark_ref
                        title_pages_added += 1
                        log_processing_stage('title_page_added', 'success', {
                            'tag': tag,
                            'title': title,
                            'title_page_path': title_page_path
                        })
                    else:
                        failed_items += 1
                        self.logger.error(f"Failed to add title page for {title}")
                        log_processing_stage('title_page_failed', 'error', {
                            'tag': tag,
                            'title': title,
                            'title_page_path': title_page_path
                        })
                else:
                    self.logger.error(f"Failed to generate title page for {title}")
                    
            elif item_type in ['document', 'cut_sheet']:
                # Add document or cut sheet
                converted_path = self.resolve_converted_path(item)
                
                if converted_path:
                    display_title = item.get('display_title', item.get('filename', 'Unknown'))
                    
                    success, start_page, end_page, bookmark_ref = self.add_pdf_to_writer(
                        writer, converted_path, f"{item_type}: {display_title}",
                        add_bookmark=True, bookmark_title=display_title,
                        bookmark_parent=current_parent_bookmark
                    )
                    
                    if success:
                        if item_type == 'document':
                            documents_added += 1
                        else:
                            cut_sheets_added += 1
                        log_processing_stage(f'{item_type}_added', 'success', {
                            'filename': item.get('filename'),
                            'display_title': display_title,
                            'converted_path': converted_path,
                            'start_page': start_page,
                            'end_page': end_page
                        })
                    else:
                        failed_items += 1
                        self.logger.error(f"Failed to add {item_type}: {display_title}")
                        log_processing_stage(f'{item_type}_failed', 'error', {
                            'filename': item.get('filename'),
                            'display_title': display_title,
                            'converted_path': converted_path
                        })
                else:
                    failed_items += 1
                    self.logger.error(f"No converted file found for: {item.get('filename', 'Unknown')}")
                    log_processing_stage('file_not_found', 'error', {
                        'filename': item.get('filename', 'Unknown'),
                        'item_type': item_type
                    })
            
            else:
                self.logger.warning(f"Unknown item type: {item_type}")
                log_processing_stage('unknown_item_type', 'warning', {
                    'item_type': item_type,
                    'item': item
                })
        
        # Write final PDF
        self.logger.info(f"\nWriting final PDF: {output_filename}")
        with open(output_filename, 'wb') as output_file:
            writer.write(output_file)
        
        self.logger.info(f"Successfully created: {output_filename}")
        
        # Log completion summary
        log_processing_stage('create_final_pdf', 'completed', {
            'output_filename': output_filename,
            'title_pages_added': title_pages_added,
            'documents_added': documents_added,
            'cut_sheets_added': cut_sheets_added,
            'failed_items': failed_items,
            'total_pages': writer.page_count if hasattr(writer, 'page_count') else 'unknown'
        })
        
        # Print summary
        total_pages = len(writer.pages)
        title_pages = len([item for item in included_items if item['type'] == 'title_page'])
        documents = len([item for item in included_items if item['type'] == 'document'])
        cut_sheets = len([item for item in included_items if item['type'] == 'cut_sheet'])
        
        self.logger.info(f"\nFinal PDF Summary:")
        self.logger.info(f"  Total pages: {total_pages}")
        self.logger.info(f"  Title pages: {title_pages}")
        self.logger.info(f"  Documents: {documents}")
        self.logger.info(f"  Cut sheets: {cut_sheets}")
        self.logger.info(f"  Total items: {len(included_items)}")
        
        return output_filename
    
    def create_file_manifest(self) -> Dict:
        """Create a manifest of what files were included/excluded"""
        manifest = {
            'included_items': [],
            'excluded_items': [],
            'summary': {}
        }
        
        for item in self.pdf_structure:
            if item.get('include', True):
                manifest['included_items'].append({
                    'type': item['type'],
                    'title': item.get('display_title') or item.get('title') or item.get('filename'),
                    'position': item.get('position', 0)
                })
            else:
                manifest['excluded_items'].append({
                    'type': item['type'],
                    'title': item.get('display_title') or item.get('title') or item.get('filename'),
                    'reason': 'Manually excluded'
                })
        
        # Summary
        manifest['summary'] = {
            'total_items': len(self.pdf_structure),
            'included_items': len(manifest['included_items']),
            'excluded_items': len(manifest['excluded_items']),
            'title_pages': len([item for item in manifest['included_items'] if item['type'] == 'title_page']),
            'documents': len([item for item in manifest['included_items'] if item['type'] == 'document']),
            'cut_sheets': len([item for item in manifest['included_items'] if item['type'] == 'cut_sheet'])
        }
        
        return manifest

def main():
    """Main function to test the assembler"""
    docs_path = r"C:\Users\jacob\Claude\python-docx\documents\CS_Air_Handler_Light_Kit"
    
    # Create assembler
    assembler = FinalPDFAssembler(docs_path)
    
    # Create final PDF
    output_filename = assembler.create_final_pdf()
    
    # Create manifest
    manifest = assembler.create_file_manifest()
    
    print(f"\nManifest:")
    print(f"  Included: {manifest['summary']['included_items']} items")
    print(f"  Excluded: {manifest['summary']['excluded_items']} items")
    
    return assembler

if __name__ == "__main__":
    assembler = main()