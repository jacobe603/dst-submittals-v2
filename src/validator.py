#!/usr/bin/env python3
"""
Input/Output validation for DST Submittals Generator V2

Provides validation methods to ensure data integrity throughout the pipeline.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

try:
    from .logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger('validator')


class ProcessingValidator:
    """
    Validates inputs and outputs for processing stages
    
    Provides comprehensive validation to catch issues early
    and provide detailed error messages for debugging.
    """
    
    @staticmethod
    def validate_input_files(file_paths: List[str]) -> Tuple[bool, str]:
        """
        Validate input files exist and are readable
        
        Args:
            file_paths: List of file paths to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_paths:
            return False, "No input files provided"
        
        if not isinstance(file_paths, list):
            return False, f"Expected list of file paths, got {type(file_paths).__name__}"
        
        missing_files = []
        unreadable_files = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
            elif not os.access(file_path, os.R_OK):
                unreadable_files.append(file_path)
        
        if missing_files:
            return False, (
                f"Missing {len(missing_files)} files:\n"
                f"{chr(10).join(missing_files[:5])}\n"
                f"{'...' if len(missing_files) > 5 else ''}"
            )
        
        if unreadable_files:
            return False, (
                f"Cannot read {len(unreadable_files)} files:\n"
                f"{chr(10).join(unreadable_files[:5])}\n"
                f"Check file permissions"
            )
        
        logger.info(f"Validated {len(file_paths)} input files successfully")
        return True, ""
    
    @staticmethod
    def validate_output_path(output_path: Path) -> Tuple[bool, str]:
        """
        Validate output path is writable
        
        Args:
            output_path: Path where output will be written
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        output_dir = output_path.parent
        
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created output directory: {output_dir}")
            except Exception as e:
                return False, f"Cannot create output directory {output_dir}: {e}"
        
        if not os.access(output_dir, os.W_OK):
            return False, f"Output directory {output_dir} is not writable"
        
        if output_path.exists() and not os.access(output_path, os.W_OK):
            return False, f"Output file {output_path} exists but is not writable"
        
        return True, ""
    
    @staticmethod
    def validate_equipment_structure(equipment_groups: Dict) -> Tuple[bool, str]:
        """
        Validate equipment groups structure
        
        Args:
            equipment_groups: Dict of equipment tags to document groups
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not equipment_groups:
            return False, "No equipment groups found"
        
        if not isinstance(equipment_groups, dict):
            return False, f"Expected dict of equipment groups, got {type(equipment_groups).__name__}"
        
        empty_groups = []
        
        for tag, docs in equipment_groups.items():
            if not docs:
                empty_groups.append(tag)
            elif isinstance(docs, dict) and '_ordered_files' in docs:
                if not docs['_ordered_files']:
                    empty_groups.append(tag)
        
        if empty_groups:
            return False, (
                f"Found {len(empty_groups)} empty equipment groups:\n"
                f"{', '.join(empty_groups)}"
            )
        
        return True, ""
    
    @staticmethod
    def validate_json_structure(json_data: Dict) -> Tuple[bool, str]:
        """
        Validate JSON structure format
        
        Args:
            json_data: JSON structure to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        required_keys = ['extraction_metadata', 'equipment_structure', 'processing_order']
        missing_keys = [key for key in required_keys if key not in json_data]
        
        if missing_keys:
            return False, f"Missing required keys in JSON: {', '.join(missing_keys)}"
        
        # Validate metadata
        metadata = json_data.get('extraction_metadata', {})
        if not metadata.get('version'):
            return False, "Missing version in extraction_metadata"
        
        # Validate equipment structure
        equipment_structure = json_data.get('equipment_structure', {})
        if not equipment_structure:
            return False, "Empty equipment_structure"
        
        # Validate processing order matches equipment
        processing_order = json_data.get('processing_order', [])
        missing_in_order = set(equipment_structure.keys()) - set(processing_order)
        
        if missing_in_order:
            return False, (
                f"Equipment tags missing from processing_order:\n"
                f"{', '.join(missing_in_order)}"
            )
        
        return True, ""
    
    @staticmethod
    def validate_pdf_output(pdf_path: Path, min_size: int = 1024) -> Tuple[bool, str]:
        """
        Validate PDF output file
        
        Args:
            pdf_path: Path to PDF file
            min_size: Minimum acceptable file size in bytes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pdf_path.exists():
            return False, f"PDF file not created: {pdf_path}"
        
        file_size = pdf_path.stat().st_size
        
        if file_size < min_size:
            return False, (
                f"PDF file too small ({file_size} bytes)\n"
                f"Minimum expected: {min_size} bytes\n"
                f"File may be corrupted or incomplete"
            )
        
        # Check if it's actually a PDF
        try:
            with open(pdf_path, 'rb') as f:
                header = f.read(4)
                if header != b'%PDF':
                    return False, (
                        f"File is not a valid PDF\n"
                        f"Header: {header}\n"
                        f"Expected: %PDF"
                    )
        except Exception as e:
            return False, f"Cannot read PDF file: {e}"
        
        logger.info(f"Validated PDF output: {pdf_path} ({file_size:,} bytes)")
        return True, ""
    
    @staticmethod
    def validate_service_health(service_info: Dict) -> Tuple[bool, str]:
        """
        Validate service health status
        
        Args:
            service_info: Service information dict
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not service_info:
            return False, "No service information available"
        
        gotenberg_status = service_info.get('gotenberg', {}).get('status')
        
        if gotenberg_status != 'healthy':
            docker_available = service_info.get('gotenberg', {}).get('docker_available', False)
            url = service_info.get('gotenberg', {}).get('url', 'unknown')
            
            return False, (
                f"Gotenberg service not healthy\n"
                f"Status: {gotenberg_status}\n"
                f"URL: {url}\n"
                f"Docker available: {docker_available}\n"
                f"Try: docker run -d --name gotenberg-service -p 3000:3000 gotenberg/gotenberg:8"
            )
        
        return True, ""


class StageResult:
    """
    Result container for pipeline stages
    
    Provides consistent result format with success status,
    data payload, and error information.
    """
    
    def __init__(self, success: bool, data: Optional[Dict] = None, 
                 error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'StageResult':
        """Create from dictionary"""
        return cls(
            success=d.get('success', False),
            data=d.get('data'),
            error=d.get('error')
        )


def test_validator():
    """Test validation functions"""
    validator = ProcessingValidator()
    
    # Test file validation
    test_files = ['/tmp/test1.pdf', '/tmp/test2.doc']
    valid, error = validator.validate_input_files(test_files)
    print(f"File validation: {valid}")
    if error:
        print(f"Error: {error}")
    
    # Test output path validation
    output_path = Path('/tmp/test_output.pdf')
    valid, error = validator.validate_output_path(output_path)
    print(f"Output path validation: {valid}")
    if error:
        print(f"Error: {error}")
    
    # Test equipment structure validation
    equipment_groups = {
        'AHU-1': {'_ordered_files': ['file1.doc', 'file2.pdf']},
        'MAU-5': {'_ordered_files': ['file3.doc']}
    }
    valid, error = validator.validate_equipment_structure(equipment_groups)
    print(f"Equipment structure validation: {valid}")
    if error:
        print(f"Error: {error}")
    
    print("\nValidation tests complete!")


if __name__ == '__main__':
    test_validator()