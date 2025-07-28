#!/usr/bin/env python3
"""
Enhanced .doc file tag extractor
Uses more aggressive string searching and filename pattern matching
"""

import os
import re
import json
from typing import Optional, Dict

def extract_tag_from_doc_advanced(file_path: str) -> Optional[str]:
    """Enhanced .doc tag extraction"""
    filename = os.path.basename(file_path)
    
    # First, try filename pattern matching
    # Files like "13_Drawing.doc" might correspond to tag "MAU-12" based on the pattern
    file_number = re.match(r'(\d+)_', filename)
    if file_number:
        num = file_number.group(1)
        
        # Load existing tag mapping to infer patterns
        try:
            with open('tag_mapping.json', 'r') as f:
                data = json.load(f)
                tag_mapping = data.get('tag_mapping', {})
                
                # Look for corresponding docx files with the same number prefix
                for mapped_filename, tag in tag_mapping.items():
                    if mapped_filename.startswith(f"{num}_") and tag:
                        print(f"  [INFERRED] {filename} -> {tag} (from {mapped_filename})")
                        return tag
        except:
            pass
    
    # Try more aggressive binary search
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Convert to string with different encodings
        text_content = ""
        encodings = ['utf-8', 'latin1', 'cp1252', 'utf-16', 'ascii']
        
        for encoding in encodings:
            try:
                text_part = content.decode(encoding, errors='ignore')
                text_content += text_part
            except:
                continue
        
        # Look for tag patterns in the combined text
        patterns = [
            r'(AHU-[A-Z0-9]+)',
            r'(MAU-[A-Z0-9]+)',
            r'Unit.{0,10}(AHU-[A-Z0-9]+)',
            r'Unit.{0,10}(MAU-[A-Z0-9]+)',
            r'Tag.{0,10}(AHU-[A-Z0-9]+)',
            r'Tag.{0,10}(MAU-[A-Z0-9]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                clean_tag = match.strip().upper()
                if clean_tag.startswith(('AHU-', 'MAU-')):
                    print(f"  [FOUND] {filename} -> {clean_tag}")
                    return clean_tag
                    
    except Exception as e:
        print(f"  [ERROR] {filename} -> {str(e)}")
    
    return None

def enhance_tag_mapping():
    """Enhance the existing tag mapping with better .doc extraction"""
    
    # Load existing mapping
    with open('tag_mapping.json', 'r') as f:
        data = json.load(f)
    
    tag_mapping = data['tag_mapping']
    docs_path = r"C:\Users\jacob\Claude\python-docx\documents\CS_Air_Handler_Light_Kit"
    
    print("ENHANCING .DOC FILE TAG EXTRACTION")
    print("="*50)
    
    # Process files that don't have tags
    enhanced_count = 0
    for filename, current_tag in tag_mapping.items():
        if not current_tag and filename.endswith('.doc'):
            file_path = os.path.join(docs_path, filename)
            if os.path.exists(file_path):
                print(f"\nProcessing: {filename}")
                new_tag = extract_tag_from_doc_advanced(file_path)
                if new_tag:
                    tag_mapping[filename] = new_tag
                    enhanced_count += 1
    
    # Update the data structure
    data['tag_mapping'] = tag_mapping
    data['tag_groups'] = create_tag_groups(tag_mapping)
    data['summary'] = {
        'total_files': len(tag_mapping),
        'files_with_tags': len([f for f in tag_mapping.values() if f]),
        'files_without_tags': len([f for f in tag_mapping.values() if not f]),
        'unique_tags': len(set([t for t in tag_mapping.values() if t]))
    }
    
    # Save enhanced mapping
    with open('tag_mapping_enhanced.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nEnhanced {enhanced_count} .doc files with tags")
    print("Enhanced mapping saved to: tag_mapping_enhanced.json")
    
    return data

def create_tag_groups(tag_mapping: Dict[str, str]) -> Dict[str, list]:
    """Create tag groups from mapping"""
    tag_groups = {}
    for filename, tag in tag_mapping.items():
        if tag:
            if tag not in tag_groups:
                tag_groups[tag] = []
            tag_groups[tag].append(filename)
    return tag_groups

def print_enhanced_summary(data):
    """Print enhanced summary"""
    tag_groups = data['tag_groups']
    
    print("\n" + "="*60)
    print("ENHANCED TAG EXTRACTION SUMMARY")
    print("="*60)
    
    print(f"Total files processed: {data['summary']['total_files']}")
    print(f"Files with tags found: {data['summary']['files_with_tags']}")
    print(f"Files without tags: {data['summary']['files_without_tags']}")
    print(f"Unique tags found: {data['summary']['unique_tags']}")
    
    print("\nTags found (ordered):")
    for tag in sorted(tag_groups.keys()):
        files = tag_groups[tag]
        print(f"\n  {tag}: {len(files)} files")
        for filename in sorted(files):
            file_type = "DOC" if filename.endswith('.doc') else "DOCX"
            print(f"    - {filename} ({file_type})")
    
    print("\nFiles still without tags:")
    no_tag_files = [f for f, t in data['tag_mapping'].items() if not t]
    for filename in no_tag_files:
        print(f"  - {filename}")

if __name__ == "__main__":
    enhanced_data = enhance_tag_mapping()
    print_enhanced_summary(enhanced_data)