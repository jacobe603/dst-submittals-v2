#!/usr/bin/env python3
"""
Configuration management for DST Submittals Generator V2
Handles environment variables and default settings for Gotenberg-based conversion
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration manager with environment variable support"""
    
    # Application version
    VERSION = "2.0.4-all-sections-fixed"  # All sections now use consistent container hierarchy
    
    def __init__(self):
        # Gotenberg service configuration
        self.gotenberg_url = self._get_env_str(
            'DST_GOTENBERG_URL',
            'http://localhost:3000'
        )
        
        # Legacy compatibility (for V1 status endpoint)
        self.officetopdf_path = None  # V2 doesn't use OfficeToPDF
        
        # Output directories
        self.converted_pdfs_dir = self._get_env_str(
            'DST_CONVERTED_PDFS_DIR',
            'converted_pdfs'
        )
        
        self.title_pages_dir = self._get_env_str(
            'DST_TITLE_PAGES_DIR', 
            'title_pages'
        )
        
        # JSON mapping files
        self.tag_mapping_file = self._get_env_str(
            'DST_TAG_MAPPING_FILE',
            'tag_mapping_enhanced.json'
        )
        
        self.pdf_conversion_mapping_file = self._get_env_str(
            'DST_PDF_CONVERSION_MAPPING_FILE',
            'pdf_conversion_mapping.json'
        )
        
        # Default test documents path (for development/testing)
        self.default_docs_path = self._get_env_path(
            'DST_DEFAULT_DOCS_PATH',
            '/Users/jacobe/Library/CloudStorage/OneDrive-SchwabVollhaberLubrattInc/Documents/DST Converter'
        )
        
        # Gotenberg quality settings
        self.quality_mode = self._get_env_str(
            'DST_QUALITY_MODE',
            'high'  # fast, balanced, high, maximum
        )
        
        # Conversion timeout settings (in seconds)
        self.conversion_timeout = self._get_env_int(
            'DST_CONVERSION_TIMEOUT',
            300  # 5 minutes for Gotenberg conversions
        )
        
        # PDF Quality settings for Gotenberg
        self.pdf_resolution = self._get_env_int(
            'DST_PDF_RESOLUTION',
            300  # DPI for image resolution in PDFs
        )
        
        self.pdf_quality = self._get_env_int(
            'DST_PDF_QUALITY',
            100  # PDF quality (0-100)
        )
        
        self.lossless_compression = self._get_env_bool(
            'DST_LOSSLESS_COMPRESSION',
            True  # Use lossless compression for technical drawings
        )
        
        # Logging configuration
        self.log_level = self._get_env_str(
            'DST_LOG_LEVEL',
            'INFO'
        )
        
        self.log_format = self._get_env_str(
            'DST_LOG_FORMAT',
            'human'  # 'human' or 'json'
        )
        
        self.log_to_console = self._get_env_bool(
            'DST_LOG_TO_CONSOLE',
            True
        )
        
        self.log_to_file = self._get_env_bool(
            'DST_LOG_TO_FILE',
            True  # Enable file logging by default for diagnostics
        )
        
        # Pipeline mode settings
        self.use_pipeline_mode = self._get_env_bool(
            'DST_USE_PIPELINE_MODE',
            False  # Default to old mode for backward compatibility
        )
        
        self.save_checkpoints = self._get_env_bool(
            'DST_SAVE_CHECKPOINTS',
            True
        )
        
        self.continue_on_failure = self._get_env_bool(
            'DST_CONTINUE_ON_FAILURE',
            False
        )
        
        # Tag extraction settings
        self.tag_extraction_mode = self._get_env_str(
            'DST_TAG_EXTRACTION_MODE',
            'filename'  # 'filename' or 'content' (filename is simpler and faster)
        )
        
        self.enable_tag_editing = self._get_env_bool(
            'DST_ENABLE_TAG_EDITING',
            False
        )
        
        self.tag_edit_mode = self._get_env_str(
            'DST_TAG_EDIT_MODE',
            'interactive'  # 'interactive', 'file', or 'api'
        )
        
        # Debug settings
        self.debug_mode = self._get_env_bool(
            'DST_DEBUG_MODE',
            False
        )
        
        self.debug_break_on_error = self._get_env_bool(
            'DST_DEBUG_BREAK_ON_ERROR',
            False
        )
        
        # Stage-specific configuration
        self.stage_config = {
            'tag_extraction': {
                'mode': self.tag_extraction_mode,
                'confidence_threshold': self._get_env_float('DST_TAG_CONFIDENCE_THRESHOLD', 0.8),
                'enable_filename_fallback': self._get_env_bool('DST_TAG_FILENAME_FALLBACK', True)
            },
            'tag_editing': {
                'enabled': self.enable_tag_editing,
                'mode': self.tag_edit_mode,
                'auto_approve_high_confidence': self._get_env_bool('DST_TAG_AUTO_APPROVE', True)
            },
            'conversion': {
                'timeout': self.conversion_timeout,
                'fallback_enabled': self._get_env_bool('DST_CONVERSION_FALLBACK', True)
            }
        }
        
        self.log_file_path = self._get_env_str(
            'DST_LOG_FILE_PATH',
            'dst_diagnostic.log'  # Dedicated diagnostic log file
        )
        
        self.file_log_level = self._get_env_str(
            'DST_FILE_LOG_LEVEL',
            'DEBUG'
        )
        
        self.log_max_bytes = self._get_env_int(
            'DST_LOG_MAX_BYTES',
            10 * 1024 * 1024  # 10MB
        )
        
        self.log_backup_count = self._get_env_int(
            'DST_LOG_BACKUP_COUNT',
            5
        )
        
        # Supported unit types - configurable list
        self.supported_unit_types = self._get_supported_unit_types()
    
    def _get_env_str(self, env_var: str, default: str) -> str:
        """Get string environment variable with default"""
        return os.getenv(env_var, default)
    
    def _get_env_int(self, env_var: str, default: int) -> int:
        """Get integer environment variable with default"""
        try:
            value = os.getenv(env_var)
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def _get_env_bool(self, env_var: str, default: bool) -> bool:
        """Get boolean environment variable with default"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _get_env_float(self, env_var: str, default: float) -> float:
        """Get float environment variable with default"""
        try:
            value = os.getenv(env_var)
            if value is None:
                return default
            return float(value)
        except ValueError:
            return default
    
    def _get_env_path(self, env_var: str, default: str) -> str:
        """Get path environment variable with default, expanding user paths"""
        path = os.getenv(env_var, default)
        return os.path.expanduser(path)
    
    def _get_supported_unit_types(self) -> list:
        """Get supported unit types from environment variable or use defaults"""
        env_types = os.getenv('DST_SUPPORTED_UNIT_TYPES')
        if env_types:
            # Parse comma-separated list from environment
            return [unit_type.strip().upper() for unit_type in env_types.split(',')]
        else:
            # Default supported unit types
            return ['AHU', 'MAU', 'HP', 'CU', 'ACCU', 'WSHP', 'FCU']
    
    def get_unit_prefixes(self) -> list:
        """Get list of unit prefixes with hyphens for regex patterns"""
        return [f"{unit_type}-" for unit_type in self.supported_unit_types]
    
    def validate_paths(self) -> dict:
        """Validate that required paths exist and return status"""
        validation_results = {}
        
        # Check OfficeToPDF availability
        validation_results['officetopdf'] = {
            'path': self.officetopdf_path,
            'exists': os.path.exists(self.officetopdf_path),
            'required': False  # Has fallbacks
        }
        
        # Check if default docs path exists (for testing)
        validation_results['default_docs'] = {
            'path': self.default_docs_path,
            'exists': os.path.exists(self.default_docs_path),
            'required': False  # Only for testing
        }
        
        return validation_results
    
    def print_config(self):
        """Print current configuration for debugging"""
        print("="*60)
        print("DST SUBMITTALS GENERATOR - CONFIGURATION")
        print("="*60)
        print(f"OfficeToPDF Path: {self.officetopdf_path}")
        print(f"Converted PDFs Dir: {self.converted_pdfs_dir}")
        print(f"Title Pages Dir: {self.title_pages_dir}")
        print(f"Tag Mapping File: {self.tag_mapping_file}")
        print(f"PDF Conversion Mapping File: {self.pdf_conversion_mapping_file}")
        print(f"Default Docs Path: {self.default_docs_path}")
        print(f"Conversion Timeout: {self.conversion_timeout}s")
        print(f"LibreOffice Timeout: {self.libreoffice_timeout}s")
        print(f"Log Level: {self.log_level}")
        print(f"Log Format: {self.log_format}")
        print(f"Log to Console: {self.log_to_console}")
        print(f"Log to File: {self.log_to_file}")
        if self.log_to_file:
            print(f"Log File Path: {self.log_file_path}")
        print(f"Supported Unit Types: {', '.join(self.supported_unit_types)}")
        
        # Validation
        validation = self.validate_paths()
        print("\nPath Validation:")
        for name, info in validation.items():
            status = "[OK]" if info['exists'] else "[MISSING]"
            req_text = "(required)" if info['required'] else "(optional)"
            print(f"  {status} {name}: {info['path']} {req_text}")


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return config


def print_env_vars_help():
    """Print help for environment variables"""
    print("""
DST Submittals Generator - Environment Variables
================================================

Tool Paths:
  DST_OFFICETOPDF_PATH          Path to OfficeToPDF.exe (default: C:\\Users\\jacob\\Downloads\\OfficeToPDF.exe)

Output Directories:
  DST_CONVERTED_PDFS_DIR        Directory for converted PDFs (default: converted_pdfs)
  DST_TITLE_PAGES_DIR           Directory for title pages (default: title_pages)

Mapping Files:
  DST_TAG_MAPPING_FILE          Tag mapping JSON file (default: tag_mapping_enhanced.json)
  DST_PDF_CONVERSION_MAPPING_FILE  PDF conversion mapping file (default: pdf_conversion_mapping.json)

Processing Settings:
  DST_CONVERSION_TIMEOUT        Conversion timeout in seconds (default: 120)
  DST_LIBREOFFICE_TIMEOUT       LibreOffice timeout in seconds (default: 60)

Development/Testing:
  DST_DEFAULT_DOCS_PATH         Default documents path for testing

Unit Type Configuration:
  DST_SUPPORTED_UNIT_TYPES      Comma-separated list of supported unit types (default: AHU,MAU,HP,CU,ACCU,WSHP,FCU)

Cleanup Configuration:
  DST_MAX_OUTPUT_FILES          Maximum number of PDF files to keep in web_outputs (default: 10)
  DST_OUTPUT_RETENTION_DAYS     Number of days to keep PDF files (default: 7)
  DST_CLEANUP_ON_STARTUP        Run cleanup at application startup (default: true)
  DST_PERIODIC_CLEANUP_HOURS    Hours between periodic cleanup runs, 0 to disable (default: 24)

Logging Configuration:
  DST_LOG_LEVEL                 Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (default: INFO)
  DST_LOG_FORMAT                Log format: 'human' or 'json' (default: human)
  DST_LOG_TO_CONSOLE            Enable console logging (default: true)
  DST_CONSOLE_LOG_LEVEL         Console log level (default: INFO)
  DST_LOG_TO_FILE               Enable file logging (default: false)
  DST_LOG_FILE_PATH             Log file path (default: dst_submittals.log)
  DST_FILE_LOG_LEVEL            File log level (default: DEBUG)
  DST_LOG_MAX_BYTES             Max log file size in bytes (default: 10485760)
  DST_LOG_BACKUP_COUNT          Number of backup log files (default: 5)

Example usage:
  set DST_OFFICETOPDF_PATH=C:\\Tools\\OfficeToPDF.exe
  set DST_CONVERTED_PDFS_DIR=output\\pdfs
  set DST_SUPPORTED_UNIT_TYPES=AHU,MAU,RTU,FCU,ERV
  set DST_LOG_TO_FILE=true
  set DST_LOG_LEVEL=DEBUG
  python dst_submittals.py "C:\\Documents\\HVAC_Submittals"
""")


if __name__ == "__main__":
    # Print configuration when run directly
    config.print_config()
    print()
    print_env_vars_help()