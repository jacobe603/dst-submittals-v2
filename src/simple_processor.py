#!/usr/bin/env python3
"""
Simplified document processor for DST Submittals Generator V2

Uses Gotenberg for conversion and simple filename-based tagging.
Much simpler and faster than the original pipeline.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    from .gotenberg_converter import GotenbergConverter
    from .simple_tag_extractor import SimpleTagExtractor
    from .logger import get_logger
    from .config import Config
    from .validator import ProcessingValidator, StageResult
except ImportError:
    from gotenberg_converter import GotenbergConverter
    from simple_tag_extractor import SimpleTagExtractor
    from logger import get_logger
    from config import Config
    from validator import ProcessingValidator, StageResult

logger = get_logger('simple_processor')


class SimpleProcessor:
    """
    Simplified document processor using Gotenberg and filename-based tagging
    
    Processes equipment documentation by:
    1. Extracting tags from filenames
    2. Grouping documents by equipment
    3. Converting each group to PDF with title page
    4. Merging all groups into final submittal
    """
    
    def __init__(self, progress_manager=None):
        self.config = Config()
        self.tag_extractor = SimpleTagExtractor()
        self.gotenberg = GotenbergConverter(self.config.gotenberg_url)
        self.progress_manager = progress_manager
        self.validator = ProcessingValidator()
        
        # Create output directories
        self.output_dir = Path('web_outputs')
        self.output_dir.mkdir(exist_ok=True)
        
        # JSON structure file path
        self.json_structure_file = Path('tag_mapping_enhanced.json')
    
    def update_progress(self, correlation_id: str, stage: str, progress: int, 
                       message: str, details: str = ""):
        """Update progress if progress manager is available"""
        if self.progress_manager:
            self.progress_manager.update_progress(correlation_id, stage, progress, message, details)
        else:
            logger.info(f"Progress {progress}%: {message}")
    
    def get_json_path(self) -> Path:
        """Get path to JSON structure file"""
        return self.json_structure_file
    
    def save_structure_to_json(self, structure_data: Dict[str, Any], correlation_id: str = None) -> bool:
        """
        Save structure data to JSON file
        
        Args:
            structure_data: Structure data from extract_tags_only
            correlation_id: Optional correlation ID for tracking
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create V2-compatible JSON structure
            json_data = {
                "extraction_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_files": structure_data.get('total_files', 0),
                    "total_equipment": structure_data.get('total_equipment', 0),
                    "correlation_id": correlation_id or "",
                    "version": "v2_hybrid"
                },
                "equipment_structure": {},
                "processing_order": structure_data.get('processing_order', [])
            }
            
            # Convert V2 structure to JSON format
            if 'structure' in structure_data:
                for equipment_tag, equipment_data in structure_data['structure'].items():
                    json_data["equipment_structure"][equipment_tag] = {
                        "order": equipment_data.get('order', 999),
                        "display_name": equipment_tag,
                        "documents": []
                    }
                    
                    # Add documents with simple position metadata (back to original format)
                    for i, doc in enumerate(equipment_data.get('documents', [])):
                        json_data["equipment_structure"][equipment_tag]["documents"].append({
                            "filename": doc.get('filename', ''),
                            "type": doc.get('type', 'other'),
                            "path": doc.get('path', ''),
                            "position": i + 1
                        })
            
            # Write to file
            with open(self.json_structure_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved structure to {self.json_structure_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save structure to JSON: {e}")
            return False
    
    def _load_or_extract_structure(self, file_paths: List[str], correlation_id: str, original_filename_map: Dict[str, str] = None) -> tuple:
        """
        Load structure from JSON or extract tags from files
        
        Args:
            file_paths: List of file paths to process
            correlation_id: Correlation ID for tracking
            original_filename_map: Optional mapping of secure filename to original filename
        
        Returns:
            Tuple of (structure_data, equipment_groups, processing_order)
        
        Raises:
            ValueError: If no equipment tags found
        """
        self.update_progress(correlation_id, 'tag_extraction', 10,
                           'Loading structure from JSON or extracting tags...',
                           'Checking for existing structure data')
        
        # Try to load from JSON first (single source of truth)
        structure_data = self.load_structure_from_json()
        
        if structure_data and structure_data.get('success'):
            logger.info("Using structure from JSON file (single source of truth)")
            processing_order = structure_data.get('processing_order', [])
            
            # Match files by filename (not path) since temp paths change between uploads
            filename_to_path = {}
            for file_path in file_paths:
                filename_to_path[os.path.basename(file_path)] = file_path
            
            # Create reverse mapping: original filename → secure filename
            original_to_secure = {}
            if original_filename_map:
                for secure_filename, original_filename in original_filename_map.items():
                    original_to_secure[original_filename] = secure_filename
                    logger.debug(f"Filename mapping: '{original_filename}' → '{secure_filename}'")
            
            # Create equipment_groups preserving JSON position order
            equipment_groups = {}
            for equipment_tag in processing_order:
                if equipment_tag in structure_data['structure']:
                    # Get documents and sort by position to preserve exact JSON order
                    documents = structure_data['structure'][equipment_tag]['documents']
                    sorted_docs = sorted(documents, key=lambda x: x.get('position', 999))
                    
                    # Create ordered file list for this equipment
                    equipment_files = []
                    for doc in sorted_docs:
                        original_filename = doc['filename']
                        # Convert original filename to secure filename for filesystem lookup
                        secure_filename = original_to_secure.get(original_filename, original_filename)
                        
                        logger.debug(f"Looking for file: original='{original_filename}' secure='{secure_filename}'")
                        
                        # Try to find matching file by secure filename
                        if secure_filename in filename_to_path:
                            actual_path = filename_to_path[secure_filename]
                            equipment_files.append(actual_path)
                            logger.debug(f"Found file: {actual_path}")
                        else:
                            logger.warning(f"File not found: '{secure_filename}' (from original: '{original_filename}')")
                            logger.debug(f"Available files: {list(filename_to_path.keys())}")
                    
                    if equipment_files:
                        # Store as special '_ordered_files' key to indicate position-based ordering
                        equipment_groups[equipment_tag] = {'_ordered_files': equipment_files}
        else:
            logger.info("No valid JSON structure found, extracting tags from files")
            equipment_groups = self.tag_extractor.extract_tags_from_files(file_paths, original_filename_map)
            processing_order = self.tag_extractor.get_processing_order(equipment_groups)
            structure_data = None
        
        if not equipment_groups:
            available_files = [os.path.basename(f) for f in file_paths[:5]]
            raise ValueError(
                f"No equipment tags found in any files\n"
                f"Checked {len(file_paths)} files\n"
                f"First few files: {available_files}\n"
                f"Expected format: 'TAG-NUMBER - Document Type.extension'"
            )
        
        # Validate equipment structure
        valid, error_msg = self.validator.validate_equipment_structure(equipment_groups)
        if not valid:
            raise ValueError(f"Equipment structure validation failed: {error_msg}")
        
        total_groups = len(equipment_groups)
        self.update_progress(correlation_id, 'tag_extraction', 20,
                           f'Found {total_groups} equipment groups',
                           f'Equipment: {", ".join(equipment_groups.keys())}')
        
        return structure_data, equipment_groups, processing_order
    
    def _convert_equipment_groups(self, equipment_groups: Dict, processing_order: List[str],
                                 quality_mode: str, correlation_id: str) -> List[str]:
        """
        Convert each equipment group to individual PDFs
        
        Args:
            equipment_groups: Dict of equipment tags to document groups
            processing_order: Order to process equipment
            quality_mode: PDF quality setting
            correlation_id: Correlation ID for tracking
        
        Returns:
            List of temporary PDF file paths
        
        Raises:
            RuntimeError: If no groups converted successfully
        """
        self.update_progress(correlation_id, 'conversion', 25,
                           'Converting documents to PDF...',
                           'Processing each equipment group')
        
        equipment_pdfs = []
        
        for i, equipment_tag in enumerate(processing_order):
            progress = 25 + int((i / len(processing_order)) * 50)  # 25-75%
            
            self.update_progress(correlation_id, 'conversion', progress,
                               f'Converting {equipment_tag}...',
                               f'Processing equipment {i+1} of {len(processing_order)}')
            
            docs = equipment_groups.get(equipment_tag, {})
            
            # Get all files for this equipment in correct order
            if '_ordered_files' in docs:
                # Using JSON position-based ordering
                equipment_files = docs['_ordered_files']
                logger.info(f"Using JSON position order for {equipment_tag}: {len(equipment_files)} files")
                for j, file_path in enumerate(equipment_files):
                    logger.info(f"  Position {j+1}: {os.path.basename(file_path)}")
            else:
                # Fallback to document type ordering
                equipment_files = []
                doc_types = self.tag_extractor.get_document_order_for_equipment(list(docs.keys()))
                
                for doc_type in doc_types:
                    if doc_type in docs:
                        equipment_files.extend(docs[doc_type])
            
            if equipment_files:
                # Create PDF for this equipment group
                temp_pdf = tempfile.mktemp(suffix=f'_{equipment_tag}.pdf')
                
                success = self.gotenberg.convert_files_to_pdf(
                    file_paths=equipment_files,
                    output_path=temp_pdf,
                    quality_mode=quality_mode,
                    equipment_tag=equipment_tag,
                    include_title_page=True
                )
                
                if success and os.path.exists(temp_pdf):
                    equipment_pdfs.append(temp_pdf)
                    logger.info(f"Successfully converted {equipment_tag}")
                else:
                    logger.warning(f"Failed to convert {equipment_tag}")
        
        if not equipment_pdfs:
            raise RuntimeError(
                f"No equipment groups were successfully converted\n"
                f"Attempted to convert {len(processing_order)} groups\n"
                f"Groups: {', '.join(processing_order)}"
            )
        
        return equipment_pdfs
    
    def _assemble_final_pdf(self, equipment_pdfs: List[str], output_path: Path,
                          structure_data: Optional[Dict], processing_order: List[str],
                          correlation_id: str) -> None:
        """
        Assemble equipment PDFs into final submittal with bookmarks
        
        Args:
            equipment_pdfs: List of PDF paths to merge
            output_path: Final output path
            structure_data: Structure data for bookmarks
            processing_order: Order of equipment tags
            correlation_id: Correlation ID for tracking
        
        Raises:
            RuntimeError: If assembly fails
        """
        self.update_progress(correlation_id, 'assembly', 80,
                           'Assembling final submittal PDF...',
                           f'Merging {len(equipment_pdfs)} equipment sections')
        
        try:
            if len(equipment_pdfs) == 1:
                # Only one PDF, just move it
                import shutil
                shutil.move(equipment_pdfs[0], output_path)
                success = True
            else:
                # Merge multiple PDFs
                success = self.gotenberg.merge_pdfs(equipment_pdfs, str(output_path))
            
            if not success or not output_path.exists():
                raise RuntimeError(
                    f"Failed to create final PDF at {output_path}\n"
                    f"Merge success: {success}\n"
                    f"File exists: {output_path.exists()}"
                )
            
            # Add PDF bookmarks/outline
            self.update_progress(correlation_id, 'assembly', 90,
                               'Adding PDF bookmarks...',
                               'Creating navigation outline')
            
            if structure_data and 'structure' in structure_data:
                # Convert V2 structure to equipment_structure format for bookmarks
                equipment_structure = {}
                for equipment_tag in processing_order:
                    if equipment_tag in structure_data['structure']:
                        equipment_structure[equipment_tag] = structure_data['structure'][equipment_tag]
                
                # Add bookmarks to the final PDF
                bookmark_success = self.gotenberg.add_bookmarks_to_pdf(
                    str(output_path), 
                    equipment_structure, 
                    processing_order
                )
                
                if bookmark_success:
                    logger.info("Successfully added PDF bookmarks")
                else:
                    logger.warning("Failed to add PDF bookmarks, but PDF generation succeeded")
            else:
                logger.info("No structure data available for bookmark creation")
        
        finally:
            # Cleanup temp files
            for temp_pdf in equipment_pdfs:
                try:
                    if os.path.exists(temp_pdf):
                        os.remove(temp_pdf)
                        logger.debug(f"Cleaned up temp file: {temp_pdf}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_pdf}: {e}")
    
    def _finalize_processing(self, output_path: Path, output_filename: str,
                           equipment_groups: Dict, file_paths: List[str],
                           quality_mode: str, correlation_id: str) -> Dict[str, Any]:
        """
        Finalize processing and return results
        
        Args:
            output_path: Path to generated PDF
            output_filename: Name of output file
            equipment_groups: Equipment groups processed
            file_paths: Original input files
            quality_mode: Quality setting used
            correlation_id: Correlation ID for tracking
        
        Returns:
            Processing summary dict
        """
        # Validate PDF output
        valid, error_msg = self.validator.validate_pdf_output(output_path)
        if not valid:
            raise RuntimeError(f"PDF output validation failed: {error_msg}")
        
        file_size = output_path.stat().st_size
        
        self.update_progress(correlation_id, 'complete', 100,
                           'Processing complete!',
                           f'Generated {output_filename} ({file_size:,} bytes)')
        
        # Save processing summary
        summary = {
            'success': True,
            'output_file': output_filename,
            'output_path': str(output_path),
            'equipment_groups': {tag: len(docs) if isinstance(docs, dict) else 1 
                               for tag, docs in equipment_groups.items()},
            'equipment_tags': list(equipment_groups.keys()),  # Add equipment tag names for UI
            'total_files': len(file_paths),
            'processing_time': datetime.now().isoformat(),
            'quality_mode': quality_mode,
            'file_size_bytes': file_size
        }
        
        logger.info(f"Processing completed successfully: {output_filename}")
        return summary
    
    def load_structure_from_json(self) -> Optional[Dict[str, Any]]:
        """
        Load structure data from JSON file
        
        Returns:
            Structure data in V2 format, or None if file doesn't exist or is invalid
        """
        try:
            if not self.json_structure_file.exists():
                logger.debug(f"JSON structure file does not exist: {self.json_structure_file}")
                return None
            
            with open(self.json_structure_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Convert JSON format back to V2 structure format
            structure_data = {
                "success": True,
                "structure": {},
                "processing_order": json_data.get('processing_order', []),
                "total_equipment": json_data.get('extraction_metadata', {}).get('total_equipment', 0),
                "total_files": json_data.get('extraction_metadata', {}).get('total_files', 0),
                "from_json": True,
                "json_timestamp": json_data.get('extraction_metadata', {}).get('timestamp', '')
            }
            
            # Convert equipment structure
            equipment_structure = json_data.get('equipment_structure', {})
            for equipment_tag, equipment_data in equipment_structure.items():
                structure_data["structure"][equipment_tag] = {
                    "order": equipment_data.get('order', 999),
                    "documents": equipment_data.get('documents', [])
                }
            
            logger.info(f"Loaded structure from {self.json_structure_file}")
            return structure_data
            
        except Exception as e:
            logger.error(f"Failed to load structure from JSON: {e}")
            return None
    
    def _prepare_processing(self, file_paths: List[str], output_filename: str, 
                           correlation_id: str) -> Path:
        """
        Prepare for processing: validate inputs and set up output path
        
        Args:
            file_paths: List of file paths to process
            output_filename: Desired output filename
            correlation_id: Correlation ID for tracking
        
        Returns:
            Path object for output file
        
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate input files
        valid, error_msg = self.validator.validate_input_files(file_paths)
        if not valid:
            raise ValueError(f"Input validation failed: {error_msg}")
        
        self.update_progress(correlation_id, 'setup', 5, 
                           'Initializing processing...',
                           f'Processing {len(file_paths)} files')
        
        if not output_filename:
            output_filename = f"DST_Submittal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        if not output_filename.lower().endswith('.pdf'):
            output_filename += '.pdf'
        
        output_path = self.output_dir / output_filename
        
        # Validate output path
        valid, error_msg = self.validator.validate_output_path(output_path)
        if not valid:
            raise ValueError(f"Output path validation failed: {error_msg}")
        
        logger.info(f"Prepared and validated output path: {output_path}")
        return output_path
    
    def process_files(self, 
                     file_paths: List[str], 
                     correlation_id: str,
                     output_filename: str = None,
                     quality_mode: str = 'high',
                     original_filename_map: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process files into submittal PDF
        
        Args:
            file_paths: List of file paths to process
            correlation_id: Unique ID for tracking this operation
            output_filename: Desired output filename
            quality_mode: Conversion quality (fast/balanced/high/maximum)
        
        Returns:
            Dict with processing results
        """
        try:
            # Step 1: Setup and validation
            output_path = self._prepare_processing(file_paths, output_filename, correlation_id)
            # Extract the actual filename that was used (in case default was generated)
            output_filename = output_path.name
            
            # Step 2: Load or extract structure
            structure_data, equipment_groups, processing_order = self._load_or_extract_structure(
                file_paths, correlation_id, original_filename_map
            )
            
            # Step 3: Convert equipment groups to PDFs
            equipment_pdfs = self._convert_equipment_groups(
                equipment_groups, processing_order, quality_mode, correlation_id
            )
            
            # Step 4: Assemble final PDF
            self._assemble_final_pdf(
                equipment_pdfs, output_path, structure_data, 
                processing_order, correlation_id
            )
            
            # Step 5: Finalize and return results
            return self._finalize_processing(
                output_path, output_filename, equipment_groups, 
                file_paths, quality_mode, correlation_id
            )
        
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            logger.error(error_msg)
            
            self.update_progress(correlation_id, 'error', 0,
                               'Processing failed',
                               error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'correlation_id': correlation_id
            }
    
    def extract_tags_only(self, file_paths: List[str], correlation_id: str = None, original_filename_map: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Extract tags from files without conversion (for preview)
        Auto-saves results to JSON for use as single source of truth
        
        Args:
            file_paths: List of file paths to analyze
            correlation_id: Optional correlation ID for tracking
            original_filename_map: Optional mapping of secure filename to original filename
        
        Returns:
            Dict with tag extraction results
        """
        try:
            equipment_groups = self.tag_extractor.extract_tags_from_files(file_paths, original_filename_map)
            processing_order = self.tag_extractor.get_processing_order(equipment_groups)
            
            # Create structure for web interface
            structure = {}
            for equipment_tag in processing_order:
                docs = equipment_groups[equipment_tag]
                doc_types = self.tag_extractor.get_document_order_for_equipment(list(docs.keys()))
                
                structure[equipment_tag] = {
                    'documents': [],
                    'order': processing_order.index(equipment_tag) + 1
                }
                
                for doc_type in doc_types:
                    if doc_type in docs:
                        for file_path in docs[doc_type]:
                            filename = os.path.basename(file_path)
                            # Use original filename for display if available
                            display_filename = filename
                            if original_filename_map and filename in original_filename_map:
                                display_filename = original_filename_map[filename]
                            structure[equipment_tag]['documents'].append({
                                'filename': display_filename,
                                'type': doc_type,
                                'path': file_path
                            })
            
            # Create result structure
            result = {
                'success': True,
                'tags': equipment_groups,
                'structure': structure,
                'processing_order': processing_order,
                'total_equipment': len(equipment_groups),
                'total_files': len(file_paths)
            }
            
            # Auto-save to JSON as single source of truth
            self.save_structure_to_json(result, correlation_id)
            logger.info(f"Extracted tags for {len(equipment_groups)} equipment groups and saved to JSON")
            
            return result
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of required services"""
        gotenberg_info = self.gotenberg.get_service_info()
        
        return {
            'gotenberg': gotenberg_info,
            'tag_extractor': {
                'status': 'ready',
                'extraction_mode': 'filename_based',
                'supported_patterns': len(self.tag_extractor.tag_patterns)
            },
            'processor': {
                'status': 'ready',
                'version': self.config.VERSION,
                'output_dir': str(self.output_dir)
            }
        }


def test_simple_processor():
    """Test the simple processor"""
    processor = SimpleProcessor()
    
    # Test service status
    status = processor.get_service_status()
    print("Service Status:")
    print(json.dumps(status, indent=2))
    
    # Test tag extraction
    test_files = [
        "AHU-1 - Technical Data Sheet.docx",
        "AHU-1 - Fan Curve.jpg",
        "MAU-5 - Technical Data Sheet.docx",
        "CS_Light_Kit.pdf"
    ]
    
    print("\nTesting tag extraction:")
    result = processor.extract_tags_only(test_files)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    test_simple_processor()