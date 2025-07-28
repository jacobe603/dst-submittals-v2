#!/usr/bin/env python3
"""
Update PDF mapping to include all successfully converted files
"""

import os
import json
import glob

def update_pdf_mapping():
    """Update the PDF mapping with all available converted files"""
    
    # Load existing tag mapping
    with open('tag_mapping_enhanced.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    tag_mapping = data['tag_mapping']
    
    # Find all converted PDFs
    converted_pdfs_dir = "converted_pdfs"
    pdf_files = glob.glob(os.path.join(converted_pdfs_dir, "*.pdf"))
    
    print(f"Found {len(pdf_files)} converted PDF files:")
    for pdf_file in pdf_files:
        print(f"  - {os.path.basename(pdf_file)}")
    
    # Create new PDF mapping
    pdf_mapping = {}
    
    for filename, tag in tag_mapping.items():
        if filename.endswith(('.doc', '.docx')):
            # Skip Item Summary files as they contain pricing
            if 'Item Summary' in filename:
                continue
                
            # Look for corresponding PDF
            base_name = os.path.splitext(filename)[0]
            pdf_path = os.path.join(converted_pdfs_dir, f"{base_name}.pdf")
            
            if os.path.exists(pdf_path):
                pdf_mapping[filename] = pdf_path
                print(f"[OK] Mapped: {filename} -> {os.path.basename(pdf_path)}")
            else:
                print(f"[SKIP] Missing: {filename} (no PDF found)")
    
    # Save updated mapping
    with open('pdf_conversion_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(pdf_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\nUpdated PDF mapping saved to: pdf_conversion_mapping.json")
    print(f"Total mapped files: {len(pdf_mapping)}")
    
    return pdf_mapping

if __name__ == "__main__":
    pdf_mapping = update_pdf_mapping()