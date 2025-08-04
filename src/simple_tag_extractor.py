#!/usr/bin/env python3
"""
Simplified filename-based tag extractor for DST Submittals Generator V2

Extracts equipment tags from filenames only, no document content parsing needed.
Much faster and simpler than content-based extraction.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger('simple_tag_extractor')


class SimpleTagExtractor:
    """
    Filename-based tag extractor for equipment identification
    
    Extracts equipment tags like AHU-1, MAU-12 from filenames and
    categorizes documents by type (technical data, fan curve, etc.)
    """
    
    def __init__(self):
        # Supported file extensions for document processing
        self.supported_extensions = {
            '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png'
        }
        
        # Equipment tag patterns - specific HVAC equipment types
        # Support both numeric (AHU-1) and alphanumeric (AHU-D4, AHU-E1, AHU-M3) tags
        # Handle both hyphen (AHU-1) and underscore (AHU_1) formats for secure_filename compatibility
        # Order matters: longer/more specific patterns first to avoid partial matches
        # NOTE: CS (cut sheet) patterns are intentionally excluded - they should not get tags
        self.tag_patterns = [
            r'(OAHU[-_][A-Z0-9]+)',      # Outdoor Air Handling Unit (must come before AHU)
            r'(WSHP[-_][A-Z0-9]+)',      # Water Source Heat Pump  
            r'(DOAS[-_][A-Z0-9]+)',      # Dedicated Outdoor Air System
            r'(BCU[-_][A-Z0-9]+)',       # Blower Coil Unit (must come before BC)
            r'(AHU[-_][A-Z0-9]+)',       # Air Handling Unit (AHU-1, AHU_1, AHU-D4, etc.)
            r'(MAU[-_][A-Z0-9]+)',       # Makeup Air Unit  
            r'(RTU[-_][A-Z0-9]+)',       # Rooftop Unit
            r'(FCU[-_][A-Z0-9]+)',       # Fan Coil Unit
            r'(HP[-_][A-Z0-9]+)',        # Heat Pump
            r'(FC[-_][A-Z0-9]+)',        # Fan Coil
            r'(BC[-_][A-Z0-9]+)',        # Blower Coil
            r'(CH[-_][A-Z0-9]+)',        # Chiller
            # Generic catch-all but exclude CS patterns (cut sheets should have no tag)
            r'(?!CS)(^[A-Z]+[A-Z0-9]*[-_][A-Z0-9]+)',  
        ]
        
        # Document type classification patterns (based on your specifications)
        # Pattern format: "TAG - Document Type.extension"
        self.doc_type_patterns = {
            'technical_data': [
                r'technical\s+data',
                r'tech\s+data',
                r'data\s+sheet',
                r'technical\s+data\s+sheet'
            ],
            'item_summary': [
                r'item\s+summary'
            ],
            'fan_curve': [
                r'fan\s+curve',
                r'curve',
                r'performance\s+curve'
            ],
            'drawing': [
                r'drawing',
                r'drawings',
                r'dwg',
                r'cad',
                r'preciseline\s+drawings',
                r'smartsource\s+drawing'
            ],
            'specification': [
                r'specification',
                r'specifications',
                r'spec',
                r'specs'
            ],
            'cutsheet': [
                r'^cs[\s_-]',      # Starts with CS followed by space, underscore, or dash
                r'cut.*sheet',
                r'cutsheet'
            ],
            'manual': [
                r'manual',
                r'instruction',
                r'operation',
                r'maintenance'
            ],
            'warranty': [
                r'warranty',
                r'guarantee'
            ]
        }
        
        # Compile regex patterns for performance
        self.compiled_tag_patterns = [re.compile(pattern, re.IGNORECASE) 
                                     for pattern in self.tag_patterns]
        
        self.compiled_doc_patterns = {}
        for doc_type, patterns in self.doc_type_patterns.items():
            self.compiled_doc_patterns[doc_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def extract_tag_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract equipment tag from filename
        
        Args:
            filename: Name of the file (with or without extension)
        
        Returns:
            Equipment tag (e.g., "AHU-1") or None if not found
        """
        # Remove file extension and clean filename
        base_name = Path(filename).stem
        
        # Skip tag extraction for cut sheet files (CS prefix)
        if base_name.upper().startswith('CS'):
            logger.debug(f"Skipping tag extraction for cut sheet file: '{filename}'")
            return None
        
        # Try each pattern
        for pattern in self.compiled_tag_patterns:
            match = pattern.search(base_name)
            if match:
                tag = match.group(1).upper()
                logger.debug(f"Found tag '{tag}' in filename '{filename}'")
                return tag
        
        logger.debug(f"No tag found in filename '{filename}'")
        return None
    
    def is_supported_file(self, filename: str) -> bool:
        """
        Check if file has supported extension
        
        Args:
            filename: Name of the file with extension
        
        Returns:
            True if file extension is supported
        """
        file_ext = Path(filename).suffix.lower()
        return file_ext in self.supported_extensions
    
    def classify_document_type(self, filename: str) -> str:
        """
        Classify document type based on filename
        Expected format: "TAG - Document Type.extension"
        
        Args:
            filename: Name of the file
        
        Returns:
            Document type classification
        """
        base_name = Path(filename).stem.lower()
        
        # Extract document type part after the " - " or secure_filename separators
        # Handle both original format and secure_filename format
        if ' - ' in base_name:
            # Original format: "TAG - Document Type"
            doc_part = base_name.split(' - ', 1)[1]
        elif '_-_' in base_name:
            # Secure format 1: "TAG_-_Document_Type" 
            doc_part = base_name.split('_-_', 1)[1].replace('_', ' ')
        elif '_' in base_name and any(base_name.startswith(prefix) for prefix in ['AHU_', 'MAU_', 'RTU_', 'FCU_', 'WSHP_', 'HP_', 'FC_', 'BC_', 'BCU_', 'DOAS_', 'OAHU_', 'CH_']):
            # Secure format 2: "TAG_Document_Type" (most common secure_filename result)
            parts = base_name.split('_', 2)
            if len(parts) >= 3:
                doc_part = '_'.join(parts[2:]).replace('_', ' ')
            else:
                doc_part = base_name
        else:
            # Use full filename if no separator
            doc_part = base_name
        
        logger.debug(f"Classifying document part: '{doc_part}' from filename: '{filename}'")
        
        # Check each document type
        for doc_type, patterns in self.compiled_doc_patterns.items():
            for pattern in patterns:
                # For cutsheet patterns, check the full base_name (not just doc_part)
                # because CS patterns need to match from the beginning
                search_text = base_name if doc_type == 'cutsheet' else doc_part
                if pattern.search(search_text):
                    logger.debug(f"Classified '{filename}' as '{doc_type}' (matched: {pattern.pattern})")
                    return doc_type
        
        # Default classification - try to be more specific
        logger.debug(f"No pattern matched for '{filename}', using default classification")
        ext = Path(filename).suffix.lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return 'drawing'  # Images are likely drawings
        elif ext in ['.pdf', '.doc', '.docx']:
            return 'technical_data'  # Default document type
        elif ext in ['.xls', '.xlsx']:
            return 'spreadsheet'
        else:
            return 'other'
    
    def extract_tags_from_files(self, file_paths: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """
        Extract tags from multiple files and organize by equipment
        
        Args:
            file_paths: List of file paths to process
        
        Returns:
            Dict organized as: {equipment_tag: {doc_type: [file_paths]}}
        """
        equipment_groups = {}
        untagged_files = []
        
        logger.info(f"Processing {len(file_paths)} files for tag extraction")
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                parent_dir = os.path.dirname(file_path) or '.'
                available_files = []
                if os.path.exists(parent_dir):
                    available_files = os.listdir(parent_dir)[:3]
                logger.warning(
                    f"File not found: {file_path}\n"
                    f"Parent directory: {parent_dir}\n"
                    f"Parent exists: {os.path.exists(parent_dir)}\n"
                    f"Sample files in parent: {available_files}"
                )
                continue
            
            filename = os.path.basename(file_path)
            
            # Skip unsupported file types
            if not self.is_supported_file(filename):
                logger.debug(f"Skipping unsupported file: {filename}")
                continue
            
            tag = self.extract_tag_from_filename(filename)
            doc_type = self.classify_document_type(filename)
            
            if tag:
                # Initialize equipment group if needed
                if tag not in equipment_groups:
                    equipment_groups[tag] = {}
                
                # Initialize document type list if needed
                if doc_type not in equipment_groups[tag]:
                    equipment_groups[tag][doc_type] = []
                
                # Add file to appropriate group
                equipment_groups[tag][doc_type].append(file_path)
                logger.debug(f"Added '{filename}' to {tag}/{doc_type}")
            else:
                # Handle untagged files (like cut sheets)
                if doc_type == 'cutsheet':
                    # Create special group for cut sheets
                    if 'CUTSHEETS' not in equipment_groups:
                        equipment_groups['CUTSHEETS'] = {}
                    if doc_type not in equipment_groups['CUTSHEETS']:
                        equipment_groups['CUTSHEETS'][doc_type] = []
                    equipment_groups['CUTSHEETS'][doc_type].append(file_path)
                    logger.debug(f"Added '{filename}' to CUTSHEETS/{doc_type}")
                else:
                    untagged_files.append(file_path)
                    logger.debug(f"No tag found for '{filename}', classified as '{doc_type}'")
        
        # Log summary
        logger.info(f"Found {len(equipment_groups)} equipment groups")
        for tag, docs in equipment_groups.items():
            doc_count = sum(len(files) for files in docs.values())
            logger.info(f"  {tag}: {doc_count} documents")
        
        if untagged_files:
            logger.info(f"Found {len(untagged_files)} untagged files")
        
        return equipment_groups
    
    def get_processing_order(self, equipment_groups: Dict) -> List[str]:
        """
        Get the correct processing order for equipment groups
        
        Args:
            equipment_groups: Dict from extract_tags_from_files
        
        Returns:
            List of equipment tags in processing order
        """
        # Separate different equipment types
        mau_tags = []
        ahu_numeric_tags = []
        ahu_alpha_tags = []
        standard_equipment_tags = []  # EF, RTU, FCU, VAV, CAV
        generic_tags = []  # Custom equipment like OAHU-1, BOILER-A
        
        for tag in equipment_groups.keys():
            if tag == 'CUTSHEETS':
                continue  # Handle cut sheets last
            elif tag.startswith('MAU-'):
                # Extract suffix for sorting (numeric or alphanumeric)
                suffix = tag.split('-')[1] if '-' in tag else ''
                try:
                    num = int(suffix)
                    mau_tags.append((num, tag))
                except (IndexError, ValueError):
                    # Non-numeric MAU tags - treat as generic
                    generic_tags.append(tag)
            elif tag.startswith('AHU-'):
                # Extract suffix for sorting
                suffix = tag.split('-')[1] if '-' in tag else ''
                try:
                    num = int(suffix)
                    ahu_numeric_tags.append((num, tag))
                except (IndexError, ValueError):
                    # Alphanumeric AHU tags (AHU-D4, AHU-E1, etc.) - sort alphabetically
                    ahu_alpha_tags.append(tag)
            elif tag.startswith(('RTU-', 'FCU-', 'WSHP-', 'HP-', 'FC-', 'BC-', 'BCU-', 'DOAS-', 'OAHU-', 'CH-')):
                # Standard HVAC equipment types
                standard_equipment_tags.append(tag)
            else:
                # Generic/custom equipment tags (OAHU-1, BOILER-A, etc.)
                generic_tags.append(tag)
        
        # Sort and create final order
        processing_order = []
        
        # 1. MAU units first (numerical order)
        mau_tags.sort(key=lambda x: x[0])
        processing_order.extend([tag for _, tag in mau_tags])
        
        # 2. AHU units second - numeric first, then alphabetical
        ahu_numeric_tags.sort(key=lambda x: x[0])
        processing_order.extend([tag for _, tag in ahu_numeric_tags])
        
        ahu_alpha_tags.sort()  # Alphabetical order for alphanumeric AHU tags
        processing_order.extend(ahu_alpha_tags)
        
        # 3. Standard HVAC equipment types (EF, RTU, FCU, VAV, CAV)
        standard_equipment_tags.sort()
        processing_order.extend(standard_equipment_tags)
        
        # 4. Generic/custom equipment tags (OAHU-1, BOILER-A, etc.) - alphabetical
        generic_tags.sort()
        processing_order.extend(generic_tags)
        
        # Cut sheets last
        if 'CUTSHEETS' in equipment_groups:
            processing_order.append('CUTSHEETS')
        
        logger.info(f"Processing order: {processing_order}")
        return processing_order
    
    def get_document_order_for_equipment(self, doc_types: List[str]) -> List[str]:
        """
        Get the correct document order within an equipment group
        
        Args:
            doc_types: List of document types for an equipment
        
        Returns:
            List of document types in correct order
        """
        # Preferred order for equipment documents (as specified by user)
        preferred_order = [
            'technical_data',       # 1. Technical Data Sheets
            'fan_curve',           # 2. Fan Curves  
            'drawing',             # 3. Drawings (includes PreciseLine, SmartSource)
            'item_summary',        # 4. Item Summary
            'specification',       # 5. Specifications
            'manual',              # 6. Manuals (if any)
            'warranty',            # 7. Warranty (if any)
            'other'                # 8. Other documents
        ]
        
        # Sort according to preferred order
        ordered_types = []
        for doc_type in preferred_order:
            if doc_type in doc_types:
                ordered_types.append(doc_type)
        
        # Add any types not in preferred order
        for doc_type in doc_types:
            if doc_type not in ordered_types:
                ordered_types.append(doc_type)
        
        return ordered_types


def test_simple_tag_extractor():
    """Test the simple tag extractor with sample filenames"""
    extractor = SimpleTagExtractor()
    
    # Test filenames
    test_files = [
        "AHU-1 - Technical Data Sheet.docx",
        "AHU-1 - Fan Curve.jpg", 
        "AHU-10 - Drawing.pdf",
        "MAU-5 - Technical Data Sheet.docx",
        "MAU-12 - Fan Curve.doc",
        "CS_Air_Handler_Light_Kit.pdf",
        "CS_Variable_Speed_Drive.pdf",
        "EF-3 - Specifications.docx",
        "Random Document.pdf"
    ]
    
    print("Testing tag extraction:")
    for filename in test_files:
        tag = extractor.extract_tag_from_filename(filename)
        doc_type = extractor.classify_document_type(filename)
        print(f"  {filename}")
        print(f"    Tag: {tag}")
        print(f"    Type: {doc_type}")
        print()
    
    # Test full processing
    print("Testing full processing:")
    equipment_groups = extractor.extract_tags_from_files(test_files)
    
    for tag, docs in equipment_groups.items():
        print(f"\n{tag}:")
        for doc_type, files in docs.items():
            print(f"  {doc_type}: {files}")
    
    # Test processing order
    print(f"\nProcessing order: {extractor.get_processing_order(equipment_groups)}")


if __name__ == '__main__':
    test_simple_tag_extractor()