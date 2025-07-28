#!/usr/bin/env python3
"""
DST Submittals Generator - Command Line Interface

Usage:
    python dst_submittals.py path/to/documents

This script provides a simple command-line interface to the DST Submittals Generator.
"""

import os
import sys
import argparse
import json
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(
        description='DST Submittals Generator - Create organized HVAC submittal PDFs',
        epilog='Example: python dst_submittals.py "C:\\Documents\\HVAC_Submittals"'
    )
    
    parser.add_argument(
        'documents_path',
        help='Path to directory containing .doc/.docx files and CS*.pdf cut sheets'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output filename for final PDF (default: auto-generated with timestamp)',
        default=None
    )
    
    parser.add_argument(
        '--no-pricing-filter',
        action='store_true',
        help='Disable automatic filtering of pages containing "$" symbols'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Verify documents path exists
    if not os.path.exists(args.documents_path):
        print(f"ERROR: Documents directory not found: {args.documents_path}")
        return 1
    
    if args.verbose:
        print("="*70)
        print("DST SUBMITTALS GENERATOR")
        print("="*70)
        print(f"Documents path: {args.documents_path}")
        print(f"Output file: {args.output or 'auto-generated'}")
        print(f"Pricing filter: {'disabled' if args.no_pricing_filter else 'enabled'}")
        print()
    
    try:
        # Import after path setup
        from tag_extractor import TagExtractor
        from enhanced_doc_extractor import enhance_tag_mapping
        from high_quality_pdf_converter import DocumentPDFConverter
        from title_page_generator import TitlePageGenerator
        from create_final_pdf import FinalPDFAssembler
        
        # Step 1: Extract tags
        if args.verbose:
            print("Step 1: Extracting tags from documents...")
        
        extractor = TagExtractor(args.documents_path)
        tag_mapping = extractor.extract_all_tags()
        
        # Call the function directly
        enhanced_mapping = enhance_tag_mapping(tag_mapping, args.documents_path)
        
        if args.verbose:
            print(f"  Found {len(tag_mapping)} documents with tags")
            print(f"  Identified {len(enhanced_mapping.get('tag_groups', {}))} equipment tags")
        
        if args.verbose:
            print(f"  Found {len(tag_mapping)} documents with tags")
            print(f"  Identified {len(enhanced_mapping.get('tag_groups', {}))} equipment tags")
        
        # Step 2: Convert to PDF
        if args.verbose:
            print("\nStep 2: Converting documents to PDF...")
        
        converter = DocumentPDFConverter(args.documents_path)
        pdf_mapping = converter.convert_all_documents(tag_mapping)
        
        # Save the pdf_mapping to a file
        with open('pdf_conversion_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(pdf_mapping, f, indent=2, ensure_ascii=False)
        
        if args.verbose:
            converter.print_conversion_summary()
        
        # Step 3: Generate title pages
        if args.verbose:
            print("\nStep 3: Generating title pages...")
        
        tags = list(enhanced_mapping.get('tag_groups', {}).keys())
        generator = TitlePageGenerator()
        title_pages = generator.create_all_title_pages(tags)
        
        # Step 4: Assemble final PDF
        if args.verbose:
            print("\nStep 4: Assembling final PDF...")
        
        assembler = FinalPDFAssembler(args.documents_path)
        final_pdf = assembler.create_final_pdf(args.output)
        
        # Success message
        print(f"\n✓ Successfully created submittal PDF: {final_pdf}")
        
        # Print summary
        manifest = assembler.create_file_manifest()
        print(f"  - {manifest['summary']['total_tags']} equipment tags processed")
        print(f"  - {manifest['summary']['total_included_files']} documents included")
        print(f"  - {manifest['summary']['cut_sheets_count']} cut sheets added")
        
        if manifest['summary']['total_excluded_files'] > 0:
            print(f"  - {manifest['summary']['total_excluded_files']} documents skipped (no PDF conversion)")
        
        return 0
        
    except ImportError as e:
        print(f"ERROR: Missing required dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())