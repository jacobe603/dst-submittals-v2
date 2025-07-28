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
    
    def add_pdf_to_writer(self, writer: PdfWriter, pdf_path: str, description: str = "") -> bool:
        """Add a PDF file to the writer, return success status"""
        try:
            if not os.path.exists(pdf_path):
                print(f"  [SKIP] File not found: {os.path.basename(pdf_path)}")
                return False
            
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            
            for page in reader.pages:
                writer.add_page(page)
            
            print(f"  [ADDED] {os.path.basename(pdf_path)} ({page_count} pages)")
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to add {os.path.basename(pdf_path)}: {e}")
            return False
    
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
            
            # Add title page for this tag
            title_page_path = os.path.join(self.title_pages_dir, f"title_{tag.replace('-', '_')}.pdf")
            self.add_pdf_to_writer(writer, title_page_path, f"Title page for {tag}")
            
            # Get files for this tag in correct order
            ordered_files = self.get_file_order_for_tag(tag)
            
            print(f"  Files for {tag} (in order):")
            for filename in ordered_files:
                # Check if we have a converted PDF for this file
                converted_pdf_path = self.pdf_mapping.get(filename)
                
                if converted_pdf_path and os.path.exists(converted_pdf_path):
                    self.add_pdf_to_writer(writer, converted_pdf_path, filename)
                else:
                    print(f"  [SKIP] No PDF available for {filename}")
            
            print()
        
        # Add CUT SHEETS section
        print("Processing CUT SHEETS section:")
        
        # Add CUT SHEETS title page
        cut_sheets_title_path = os.path.join(self.title_pages_dir, "title_CUT_SHEETS.pdf")
        self.add_pdf_to_writer(writer, cut_sheets_title_path, "CUT SHEETS title page")
        
        # Add all CS*.pdf files
        cs_pdfs = self.get_cs_pdf_files()
        print(f"  Adding {len(cs_pdfs)} cut sheet files:")
        
        for cs_pdf in cs_pdfs:
            self.add_pdf_to_writer(writer, cs_pdf, f"Cut sheet: {os.path.basename(cs_pdf)}")
        
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
    """Main function to create the final PDF"""
    docs_path = r"C:\Users\jacob\Claude\python-docx\documents\CS_Air_Handler_Light_Kit"
    
    # Create final PDF assembler
    assembler = FinalPDFAssembler(docs_path)
    
    # Create manifest
    manifest = assembler.create_file_manifest()
    
    # Save manifest
    with open('final_pdf_manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("File manifest created: final_pdf_manifest.json")
    print("\nManifest Summary:")
    print(f"  Total tags: {manifest['summary']['total_tags']}")
    print(f"  Included files: {manifest['summary']['total_included_files']}")
    print(f"  Excluded files: {manifest['summary']['total_excluded_files']}")
    print(f"  Cut sheets: {manifest['summary']['cut_sheets_count']}")
    
    # Show excluded files
    if manifest['summary']['total_excluded_files'] > 0:
        print("\nExcluded files (no PDF conversion available):")
        for tag, excluded_files in manifest['excluded_files'].items():
            if excluded_files:
                print(f"  {tag}: {', '.join(excluded_files)}")
    
    # Create final PDF
    final_pdf = assembler.create_final_pdf()
    
    return assembler, final_pdf

if __name__ == "__main__":
    assembler, final_pdf = main()