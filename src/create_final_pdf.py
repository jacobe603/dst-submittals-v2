#!/usr/bin/env python3
"""
Create the final tag-ordered PDF with proper document ordering and title pages
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Optional
from pypdf import PdfReader, PdfWriter
from title_page_generator import TitlePageGenerator

class FinalPDFAssembler:
    def __init__(self, docs_path: str, converted_pdfs_dir: str = "converted_pdfs", 
                 title_pages_dir: str = "title_pages"):
        self.docs_path = docs_path
        self.converted_pdfs_dir = converted_pdfs_dir
        self.title_pages_dir = title_pages_dir
        self.load_mappings()
        
    def load_mappings(self):
        """Load tag mapping and PDF conversion mapping"""
        # Load tag mapping
        with open('tag_mapping_enhanced.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.tag_mapping = data['tag_mapping']
        self.tag_groups = data['tag_groups']
        
        # Load PDF conversion mapping
        try:
            with open('pdf_conversion_mapping.json', 'r', encoding='utf-8') as f:
                self.pdf_mapping = json.load(f)
        except FileNotFoundError:
            self.pdf_mapping = {}
            print("Warning: PDF conversion mapping not found")
    
    def get_cs_pdf_files(self) -> List[str]:
        """Get all CS*.pdf files for cut sheets section"""
        cs_pdfs = glob.glob(os.path.join(self.docs_path, "CS*.pdf"))
        return sorted(cs_pdfs)
    
    def get_file_order_for_tag(self, tag: str) -> List[str]:
        """Get files for a tag in the specified order: Technical Data Sheet, Fan Curve, Drawing"""
        files_for_tag = self.tag_groups.get(tag, [])
        
        ordered_files = []
        file_types = {
            'technical': [],
            'fan_curve': [],
            'drawing': [],
            'other': []
        }
        
        # Categorize files
        for filename in files_for_tag:
            if 'Technical Data Sheet' in filename:
                file_types['technical'].append(filename)
            elif 'Fan Curve' in filename:
                file_types['fan_curve'].append(filename)
            elif 'Drawing' in filename:
                file_types['drawing'].append(filename)
            else:
                file_types['other'].append(filename)
        
        # Add in specified order: Technical Data Sheet, Fan Curve, Drawing
        ordered_files.extend(sorted(file_types['technical']))
        ordered_files.extend(sorted(file_types['fan_curve']))
        ordered_files.extend(sorted(file_types['drawing']))
        ordered_files.extend(sorted(file_types['other']))  # Any other files
        
        return ordered_files
    
    def add_pdf_to_writer(self, writer: PdfWriter, pdf_path: str, description: str = "", 
                          add_bookmark: bool = False, bookmark_title: str = None, 
                          bookmark_parent=None) -> tuple:
        """Add a PDF file to the writer, optionally add bookmark, return (success, start_page, end_page, bookmark_ref)"""
        try:
            if not os.path.exists(pdf_path):
                print(f"  [SKIP] File not found: {os.path.basename(pdf_path)}")
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
            
            print(f"  [ADDED] {os.path.basename(pdf_path)} ({page_count} pages)")
            return True, start_page, end_page, bookmark_ref
            
        except Exception as e:
            print(f"  [ERROR] Failed to add {os.path.basename(pdf_path)}: {e}")
            return False, None, None, None
    
    def create_final_pdf(self, output_filename: str = None) -> str:
        """Create the final tag-ordered PDF document"""
        if not output_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"CS_Air_Handler_Final_Document_{timestamp}.pdf"
        
        print("="*70)
        print("CREATING FINAL TAG-ORDERED PDF DOCUMENT")
        print("="*70)
        
        writer = PdfWriter()
        
        # Get sorted tags
        sorted_tags = sorted(self.tag_groups.keys(), key=lambda x: (
            x.startswith('MAU-'),  # MAU tags first
            x.replace('AHU-', '').replace('MAU-', '').zfill(10)  # Then AHU tags sorted numerically
        ))
        
        print(f"Processing {len(sorted_tags)} tags in order:")
        for i, tag in enumerate(sorted_tags):
            print(f"  {i+1}. {tag}")
        print()
        
        # Process each tag
        for tag in sorted_tags:
            print(f"Processing TAG: {tag}")
            
            # Add title page for this tag with main bookmark
            title_page_path = os.path.join(self.title_pages_dir, f"title_{tag.replace('-', '_')}.pdf")
            success, start_page, end_page, tag_bookmark = self.add_pdf_to_writer(
                writer, title_page_path, f"Title page for {tag}", 
                add_bookmark=True, bookmark_title=tag
            )
            
            # Get files for this tag in correct order
            ordered_files = self.get_file_order_for_tag(tag)
            
            print(f"  Files for {tag} (in order):")
            for filename in ordered_files:
                # Check if we have a converted PDF for this file
                converted_pdf_path = self.pdf_mapping.get(filename)
                
                if converted_pdf_path and os.path.exists(converted_pdf_path):
                    # Create a clean bookmark title from filename
                    clean_filename = os.path.splitext(filename)[0]
                    # Remove the numeric prefix (e.g., "10_" from "10_Technical Data Sheet")
                    clean_title = clean_filename.replace('_', ' ').strip()
                    if clean_title.split()[0].isdigit():
                        clean_title = ' '.join(clean_title.split()[1:])
                    
                    self.add_pdf_to_writer(
                        writer, converted_pdf_path, filename,
                        add_bookmark=True, bookmark_title=clean_title, 
                        bookmark_parent=tag_bookmark
                    )
                else:
                    print(f"  [SKIP] No PDF available for {filename}")
            
            print()
        
        # Add CUT SHEETS section
        print("Processing CUT SHEETS section:")
        
        # Add CUT SHEETS title page with main bookmark
        cut_sheets_title_path = os.path.join(self.title_pages_dir, "title_CUT_SHEETS.pdf")
        success, start_page, end_page, cut_sheets_bookmark = self.add_pdf_to_writer(
            writer, cut_sheets_title_path, "CUT SHEETS title page",
            add_bookmark=True, bookmark_title="CUT SHEETS"
        )
        
        # Add all CS*.pdf files
        cs_pdfs = self.get_cs_pdf_files()
        print(f"  Adding {len(cs_pdfs)} cut sheet files:")
        
        for cs_pdf in cs_pdfs:
            # Create clean bookmark title from filename
            filename = os.path.basename(cs_pdf)
            clean_title = os.path.splitext(filename)[0]
            # Remove "CS_" prefix and replace underscores with spaces
            if clean_title.startswith('CS_'):
                clean_title = clean_title[3:].replace('_', ' ')
            
            self.add_pdf_to_writer(
                writer, cs_pdf, f"Cut sheet: {filename}",
                add_bookmark=True, bookmark_title=clean_title,
                bookmark_parent=cut_sheets_bookmark
            )
        
        # Write final PDF
        print(f"\nWriting final PDF: {output_filename}")
        with open(output_filename, 'wb') as output_file:
            writer.write(output_file)
        
        print(f"Successfully created: {output_filename}")
        
        # Print summary
        total_pages = len(writer.pages)
        print(f"\nFinal PDF Summary:")
        print(f"  Total pages: {total_pages}")
        print(f"  Tags processed: {len(sorted_tags)}")
        print(f"  Cut sheets added: {len(cs_pdfs)}")
        
        return output_filename
    
    def create_file_manifest(self) -> Dict:
        """Create a manifest of what files were included/excluded"""
        manifest = {
            'included_files': {},
            'excluded_files': {},
            'summary': {}
        }
        
        for tag in self.tag_groups.keys():
            ordered_files = self.get_file_order_for_tag(tag)
            
            included = []
            excluded = []
            
            for filename in ordered_files:
                converted_pdf_path = self.pdf_mapping.get(filename)
                if converted_pdf_path and os.path.exists(converted_pdf_path):
                    included.append(filename)
                else:
                    excluded.append(filename)
            
            manifest['included_files'][tag] = included
            manifest['excluded_files'][tag] = excluded
        
        # Add cut sheets
        cs_pdfs = self.get_cs_pdf_files()
        manifest['cut_sheets'] = [os.path.basename(f) for f in cs_pdfs]
        
        # Summary
        total_included = sum(len(files) for files in manifest['included_files'].values())
        total_excluded = sum(len(files) for files in manifest['excluded_files'].values())
        
        manifest['summary'] = {
            'total_tags': len(self.tag_groups),
            'total_included_files': total_included,
            'total_excluded_files': total_excluded,
            'cut_sheets_count': len(cs_pdfs)
        }
        
        return manifest

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
