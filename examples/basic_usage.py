#!/usr/bin/env python3
"""
DST Submittals Generator - Basic Usage Example

This script demonstrates how to use the DST Submittals Generator
to process HVAC documents and create organized submittal PDFs.
"""

import os
import sys
import json
from datetime import datetime

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tag_extractor import TagExtractor
from enhanced_doc_extractor import EnhancedDocExtractor  
from high_quality_pdf_converter import DocumentPDFConverter
from title_page_generator import TitlePageGenerator
from create_final_pdf import FinalPDFAssembler

def main():
    """
    Main function demonstrating complete workflow:
    1. Extract tags from documents
    2. Convert documents to PDF
    3. Generate title pages
    4. Assemble final organized PDF
    """
    
    # Configuration - Update this path to your documents directory
    DOCS_PATH = r"C:\path\to\your\hvac\documents"
    
    print("="*70)
    print("DST SUBMITTALS GENERATOR - BASIC USAGE EXAMPLE")
    print("="*70)
    
    # Step 1: Verify documents directory exists
    if not os.path.exists(DOCS_PATH):
        print(f"ERROR: Documents directory not found: {DOCS_PATH}")
        print("Please update DOCS_PATH in this script to point to your documents.")
        return False
    
    print(f"Processing documents from: {DOCS_PATH}")
    
    try:
        # Step 2: Extract tags from documents
        print("\n" + "="*50)
        print("STEP 1: EXTRACTING TAGS FROM DOCUMENTS")
        print("="*50)
        
        extractor = TagExtractor(DOCS_PATH)
        tag_mapping = extractor.extract_all_tags()
        
        # Also try enhanced extraction for .doc files
        enhanced_extractor = EnhancedDocExtractor(DOCS_PATH)
        enhanced_mapping = enhanced_extractor.create_enhanced_mapping(tag_mapping)
        
        print(f"Extracted {len(tag_mapping)} document mappings")
        
        # Save tag mapping for reference
        with open('tag_mapping_example.json', 'w', encoding='utf-8') as f:
            json.dump({
                'tag_mapping': tag_mapping,
                'tag_groups': enhanced_mapping.get('tag_groups', {})
            }, f, indent=2, ensure_ascii=False)
        
        # Step 3: Convert documents to PDF
        print("\n" + "="*50)
        print("STEP 2: CONVERTING DOCUMENTS TO PDF")
        print("="*50)
        
        converter = DocumentPDFConverter(DOCS_PATH)
        pdf_mapping = converter.convert_all_documents(tag_mapping)
        
        # Print conversion summary
        converter.print_conversion_summary()
        
        # Save PDF mapping
        with open('pdf_mapping_example.json', 'w', encoding='utf-8') as f:
            json.dump(pdf_mapping, f, indent=2, ensure_ascii=False)
        
        # Step 4: Generate title pages
        print("\n" + "="*50)
        print("STEP 3: GENERATING TITLE PAGES")
        print("="*50)
        
        # Get unique tags for title pages
        tags = list(enhanced_mapping.get('tag_groups', {}).keys())
        sorted_tags = sorted(tags, key=lambda x: (
            x.startswith('MAU-'),  # MAU tags first
            x.replace('AHU-', '').replace('MAU-', '').zfill(10)  # Then AHU tags
        ))
        
        generator = TitlePageGenerator()
        title_pages = generator.create_all_title_pages(sorted_tags)
        
        # Step 5: Assemble final PDF
        print("\n" + "="*50)
        print("STEP 4: ASSEMBLING FINAL PDF")
        print("="*50)
        
        assembler = FinalPDFAssembler(DOCS_PATH)
        final_pdf = assembler.create_final_pdf()
        
        # Step 6: Create manifest
        print("\n" + "="*50)
        print("STEP 5: CREATING FILE MANIFEST")
        print("="*50)
        
        manifest = assembler.create_file_manifest()
        
        with open('final_manifest_example.json', 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        # Print success summary
        print("\n" + "="*70)
        print("SUCCESS! SUBMITTAL PDF GENERATION COMPLETE")
        print("="*70)
        print(f"Final PDF: {final_pdf}")
        print(f"Total pages: {len(assembler.tag_groups)} tag sections + cut sheets")
        print(f"Documents processed: {manifest['summary']['total_included_files']}")
        print(f"Cut sheets included: {manifest['summary']['cut_sheets_count']}")
        
        if manifest['summary']['total_excluded_files'] > 0:
            print(f"Documents skipped: {manifest['summary']['total_excluded_files']} (no PDF conversion)")
        
        print(f"\nGenerated files:")
        print(f"  - {final_pdf}")
        print(f"  - tag_mapping_example.json")
        print(f"  - pdf_mapping_example.json") 
        print(f"  - final_manifest_example.json")
        print(f"  - title_pages/ (directory)")
        print(f"  - converted_pdfs/ (directory)")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        print("Please check your documents directory and ensure all requirements are installed.")
        return False

def quick_test():
    """
    Quick test function to verify the system is working
    """
    print("Testing DST Submittals Generator components...")
    
    try:
        # Test imports
        from tag_extractor import TagExtractor
        from high_quality_pdf_converter import DocumentPDFConverter
        from title_page_generator import TitlePageGenerator
        from create_final_pdf import FinalPDFAssembler
        print("✓ All modules imported successfully")
        
        # Test Word COM availability
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.Quit()
            print("✓ Microsoft Word COM automation available")
        except Exception as e:
            print(f"⚠ Word COM not available: {e}")
        
        # Test other dependencies
        import pypdf
        import reportlab
        import docx
        print("✓ All dependencies available")
        
        print("\nSystem is ready! Run main() with your documents path.")
        return True
        
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    # Run quick test first
    if quick_test():
        print("\n" + "="*50)
        
        # Ask user if they want to run the full example
        response = input("Run full example? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            success = main()
            if success:
                print("\nExample completed successfully!")
            else:
                print("\nExample failed. Please check configuration and try again.")
        else:
            print("Skipping full example. Update DOCS_PATH and run main() when ready.")
    else:
        print("System check failed. Please install requirements and try again.")