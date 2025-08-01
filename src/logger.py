#!/usr/bin/env python3
"""
Centralized logging system for DST Submittals Generator
Provides structured logging with correlation IDs and configurable outputs
"""

import logging
import logging.handlers
import json
import uuid
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import threading

try:
    from .config import get_config
except ImportError:
    # Handle case when running as standalone script
    from config import get_config


class CorrelationIDFilter(logging.Filter):
    """Filter to inject correlation ID into log records"""
    
    def filter(self, record):
        # Get correlation ID from thread-local storage, or create new one
        correlation_id = getattr(threading.current_thread(), 'correlation_id', None)
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]
            threading.current_thread().correlation_id = correlation_id
        
        record.correlation_id = correlation_id
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'correlation_id': getattr(record, 'correlation_id', 'unknown'),
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
            
        return json.dumps(log_entry, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output"""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record):
        correlation_id = getattr(record, 'correlation_id', 'unknown')
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Color coding for different log levels
        level_colors = {
            'DEBUG': '\033[36m',     # Cyan
            'INFO': '\033[32m',      # Green  
            'WARNING': '\033[33m',   # Yellow
            'ERROR': '\033[31m',     # Red
            'CRITICAL': '\033[41m',  # Red background
        }
        
        reset_color = '\033[0m'
        level_color = level_colors.get(record.levelname, '')
        
        # Format: [HH:MM:SS] [LEVEL] [correlation_id] module.function:line - message
        base_format = f"[{timestamp}] [{level_color}{record.levelname:8}{reset_color}] [{correlation_id}] {record.module}.{record.funcName}:{record.lineno} - {record.getMessage()}"
        
        # Add exception information if present
        if record.exc_info:
            exception_info = ''.join(traceback.format_exception(*record.exc_info))
            base_format += f"\n{exception_info}"
            
        return base_format


class DSTLogger:
    """Main logger class for DST Submittals Generator"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.config = get_config()
            self.correlation_filter = CorrelationIDFilter()
            self._setup_logging()
            self._initialized = True
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Get root logger
        self.logger = logging.getLogger('dst_submittals')
        self.logger.setLevel(getattr(logging, self.config.log_level.upper()))
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Add correlation ID filter
        self.logger.addFilter(self.correlation_filter)
        
        # Setup console handler
        if self.config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.log_level.upper()))
            
            if self.config.log_format == 'json':
                console_handler.setFormatter(JSONFormatter())
            else:
                console_handler.setFormatter(HumanReadableFormatter())
                
            self.logger.addHandler(console_handler)
        
        # Setup file handler
        if self.config.log_to_file and self.config.log_file_path:
            # Ensure log directory exists
            log_file = Path(self.config.log_file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent huge log files
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.log_file_path,
                maxBytes=self.config.log_max_bytes,
                backupCount=self.config.log_backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, self.config.file_log_level.upper()))
            file_handler.setFormatter(JSONFormatter())  # Always use JSON for file logs
            
            self.logger.addHandler(file_handler)
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Get a logger instance with optional name suffix"""
        if name:
            return logging.getLogger(f'dst_submittals.{name}')
        return self.logger
    
    def set_correlation_id(self, correlation_id: str = None):
        """Set correlation ID for current thread"""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())[:8]
        threading.current_thread().correlation_id = correlation_id
        return correlation_id
    
    def get_correlation_id(self) -> str:
        """Get current correlation ID"""
        return getattr(threading.current_thread(), 'correlation_id', 'unknown')
    
    def log_operation_start(self, operation: str, **kwargs):
        """Log the start of an operation"""
        logger = self.get_logger('operations')
        extra_data = {'operation': operation, 'status': 'started'}
        extra_data.update(kwargs)
        logger.info(f"Starting operation: {operation}", extra=extra_data)
    
    def log_operation_success(self, operation: str, duration: float = None, **kwargs):
        """Log successful operation completion"""
        logger = self.get_logger('operations')
        extra_data = {'operation': operation, 'status': 'success'}
        if duration is not None:
            extra_data['duration_seconds'] = duration
        extra_data.update(kwargs)
        logger.info(f"Operation completed successfully: {operation}", extra=extra_data)
    
    def log_operation_failure(self, operation: str, error: Exception, duration: float = None, **kwargs):
        """Log operation failure"""
        logger = self.get_logger('operations')
        extra_data = {
            'operation': operation, 
            'status': 'failed',
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        if duration is not None:
            extra_data['duration_seconds'] = duration
        extra_data.update(kwargs)
        logger.error(f"Operation failed: {operation}", extra=extra_data, exc_info=True)
    
    def log_progress(self, operation: str, current: int, total: int, **kwargs):
        """Log progress information"""
        logger = self.get_logger('progress')
        percentage = (current / total * 100) if total > 0 else 0
        extra_data = {
            'operation': operation,
            'current': current,
            'total': total,
            'percentage': round(percentage, 1)
        }
        extra_data.update(kwargs)
        logger.info(f"Progress {operation}: {current}/{total} ({percentage:.1f}%)", extra=extra_data)


# Global logger instance
_dst_logger = None


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    return _dst_logger.get_logger(name)


def set_correlation_id(correlation_id: str = None) -> str:
    """Set correlation ID for current thread"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    return _dst_logger.set_correlation_id(correlation_id)


def get_correlation_id() -> str:
    """Get current correlation ID"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    return _dst_logger.get_correlation_id()


def log_operation_start(operation: str, **kwargs):
    """Log the start of an operation"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    _dst_logger.log_operation_start(operation, **kwargs)


def log_operation_success(operation: str, duration: float = None, **kwargs):
    """Log successful operation completion"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    _dst_logger.log_operation_success(operation, duration, **kwargs)


def log_operation_failure(operation: str, error: Exception, duration: float = None, **kwargs):
    """Log operation failure"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    _dst_logger.log_operation_failure(operation, error, duration, **kwargs)


def log_progress(operation: str, current: int, total: int, **kwargs):
    """Log progress information"""
    global _dst_logger
    if _dst_logger is None:
        _dst_logger = DSTLogger()
    _dst_logger.log_progress(operation, current, total, **kwargs)


# Specialized Diagnostic Logging Functions

def log_file_upload(original_name: str, secured_name: str, file_size: int, temp_path: str, **kwargs):
    """Log detailed file upload information"""
    logger = get_logger('diagnostic.upload')
    extra_data = {
        'original_name': original_name,
        'secured_name': secured_name,
        'file_size': file_size,
        'temp_path': temp_path,
        'operation': 'file_upload'
    }
    extra_data.update(kwargs)
    logger.info(f"File uploaded: {original_name} -> {secured_name} ({file_size} bytes)", extra=extra_data)


def log_tag_extraction(filename: str, method: str, success: bool, tag_found: str = None, 
                      patterns_tested: list = None, **kwargs):
    """Log detailed tag extraction information"""
    logger = get_logger('diagnostic.tags')
    extra_data = {
        'target_filename': filename,  # Renamed to avoid LogRecord conflict
        'extraction_method': method,
        'success': success,
        'tag_found': tag_found,
        'patterns_tested': patterns_tested or [],
        'operation': 'tag_extraction'
    }
    extra_data.update(kwargs)
    
    if success:
        logger.info(f"Tag extracted: {filename} -> {tag_found} (method: {method})", extra=extra_data)
    else:
        logger.warning(f"Tag extraction failed: {filename} (method: {method})", extra=extra_data)


def log_pdf_structure(structure: list, metadata: dict, processing_options: dict, **kwargs):
    """Log complete PDF structure information"""
    logger = get_logger('diagnostic.structure')
    extra_data = {
        'structure_items': len(structure),
        'metadata': metadata,
        'processing_options': processing_options,
        'operation': 'pdf_structure_generation'
    }
    extra_data.update(kwargs)
    
    # Log summary
    logger.info(f"PDF structure generated: {len(structure)} items", extra=extra_data)
    
    # Log detailed structure (limited to avoid huge logs)
    for i, item in enumerate(structure[:10]):  # Log first 10 items
        item_data = {
            'position': i + 1,
            'type': item.get('type'),
            'title': item.get('display_title') or item.get('title'),
            'filename': item.get('filename'),
            'include': item.get('include', True),
            'operation': 'pdf_structure_item'
        }
        logger.debug(f"Structure item {i+1}: {item.get('type')} - {item.get('display_title', 'N/A')}", extra=item_data)
    
    if len(structure) > 10:
        logger.debug(f"... and {len(structure) - 10} more structure items", extra={'operation': 'pdf_structure_truncated'})


def log_file_conversion(source: str, destination: str, method: str, success: bool, 
                       error: str = None, **kwargs):
    """Log detailed file conversion information"""
    logger = get_logger('diagnostic.conversion')
    extra_data = {
        'source_file': source,
        'destination_file': destination,
        'conversion_method': method,
        'success': success,
        'error_message': error,  # Renamed to avoid LogRecord conflict
        'operation': 'file_conversion'
    }
    extra_data.update(kwargs)
    
    if success:
        logger.info(f"File converted: {source} -> {destination} (method: {method})", extra=extra_data)
    else:
        logger.error(f"Conversion failed: {source} -> {destination} (method: {method}): {error}", extra=extra_data)


def log_json_snapshot(data_type: str, data: Any, correlation_id: str = None, **kwargs):
    """Log JSON snapshot of important data structures"""
    logger = get_logger('diagnostic.snapshots')
    
    # Convert data to JSON-serializable format
    try:
        import json
        json_data = json.dumps(data, default=str, indent=2)[:2000]  # Limit size
        if len(str(data)) > 2000:
            json_data += "\n... (truncated)"
    except Exception as e:
        json_data = f"<Could not serialize data: {e}>"
    
    extra_data = {
        'data_type': data_type,
        'data_size': len(str(data)),
        'correlation_id': correlation_id or get_correlation_id(),
        'operation': 'json_snapshot'
    }
    extra_data.update(kwargs)
    
    logger.debug(f"JSON snapshot ({data_type}):\n{json_data}", extra=extra_data)


def log_file_manifest(temp_dir: str, files_found: list, **kwargs):
    """Log manifest of files in temporary directory"""
    logger = get_logger('diagnostic.manifest')
    extra_data = {
        'temp_directory': temp_dir,
        'file_count': len(files_found),
        'files': files_found,
        'operation': 'file_manifest'
    }
    extra_data.update(kwargs)
    
    logger.info(f"File manifest: {len(files_found)} files in {temp_dir}", extra=extra_data)
    for i, file_info in enumerate(files_found[:20]):  # Log first 20 files
        logger.debug(f"  {i+1}: {file_info}", extra={'operation': 'manifest_item', 'file_info': file_info})


def log_processing_stage(stage: str, status: str, details: dict = None, **kwargs):
    """Log processing stage information"""
    logger = get_logger('diagnostic.stages')
    extra_data = {
        'stage': stage,
        'status': status,
        'details': details or {},
        'operation': 'processing_stage'
    }
    extra_data.update(kwargs)
    
    logger.info(f"Processing stage: {stage} - {status}", extra=extra_data)


if __name__ == "__main__":
    # Test the logging system
    logger = get_logger('test')
    
    set_correlation_id('test-123')
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.error("Caught exception", exc_info=True)
    
    log_operation_start("test_operation", file_count=5)
    log_progress("test_operation", 3, 5)
    log_operation_success("test_operation", duration=1.5, files_processed=5)