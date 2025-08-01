"""Enhanced debug logging with file output"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class DebugLogger:
    """Enhanced logger with file output and structured logging"""
    
    def __init__(self, name: str, log_dir: Optional[str] = None, 
                 correlation_id: Optional[str] = None,
                 log_level: str = "INFO"):
        self.name = name
        self.correlation_id = correlation_id or self._generate_correlation_id()
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Set up log directory
        if log_dir:
            self.log_dir = log_dir
        else:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            self.log_dir = os.path.join('debug_logs', f'{timestamp}_{self.correlation_id}')
            
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up logger
        self.logger = self._setup_logger()
        
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        import uuid
        return str(uuid.uuid4())[:8]
        
    def _setup_logger(self) -> logging.Logger:
        """Set up Python logger with file and console handlers"""
        logger = logging.getLogger(f"{self.name}_{self.correlation_id}")
        logger.setLevel(self.log_level)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Console handler with simple format
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler with detailed format
        log_file = os.path.join(self.log_dir, f'{self.name}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(correlation_id)s] %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
        # JSON handler for structured logging
        json_file = os.path.join(self.log_dir, f'{self.name}.json')
        self.json_handler = JsonFileHandler(json_file, self.correlation_id)
        logger.addHandler(self.json_handler)
        
        return logger
        
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data"""
        self.logger.debug(message, extra={'correlation_id': self.correlation_id})
        if kwargs:
            self.json_handler.log_structured('DEBUG', message, kwargs)
            
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data"""
        self.logger.info(message, extra={'correlation_id': self.correlation_id})
        if kwargs:
            self.json_handler.log_structured('INFO', message, kwargs)
            
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data"""
        self.logger.warning(message, extra={'correlation_id': self.correlation_id})
        if kwargs:
            self.json_handler.log_structured('WARNING', message, kwargs)
            
    def error(self, message: str, **kwargs):
        """Log error message with optional structured data"""
        self.logger.error(message, extra={'correlation_id': self.correlation_id})
        if kwargs:
            self.json_handler.log_structured('ERROR', message, kwargs)
            
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, extra={'correlation_id': self.correlation_id})
        if kwargs:
            self.json_handler.log_structured('ERROR', message, kwargs, include_traceback=True)
            
    def log_stage_start(self, stage_name: str, config: Dict[str, Any]):
        """Log the start of a pipeline stage"""
        self.info(f"Starting stage: {stage_name}", stage=stage_name, config=config)
        
    def log_stage_end(self, stage_name: str, success: bool, duration: float, 
                      error: Optional[str] = None):
        """Log the end of a pipeline stage"""
        if success:
            self.info(
                f"Stage completed: {stage_name} ({duration:.2f}s)",
                stage=stage_name, duration=duration, success=True
            )
        else:
            self.error(
                f"Stage failed: {stage_name} ({duration:.2f}s) - {error}",
                stage=stage_name, duration=duration, success=False, error=error
            )
            
    def log_file_operation(self, operation: str, filepath: str, 
                          success: bool, details: Optional[Dict[str, Any]] = None):
        """Log file operations with details"""
        if success:
            self.info(
                f"{operation}: {filepath}",
                operation=operation, filepath=filepath, success=True, **(details or {})
            )
        else:
            self.error(
                f"{operation} failed: {filepath}",
                operation=operation, filepath=filepath, success=False, **(details or {})
            )
            
    def create_stage_logger(self, stage_name: str) -> 'DebugLogger':
        """Create a sub-logger for a specific stage"""
        stage_log_dir = os.path.join(self.log_dir, 'stages')
        os.makedirs(stage_log_dir, exist_ok=True)
        
        return DebugLogger(
            name=stage_name,
            log_dir=stage_log_dir,
            correlation_id=self.correlation_id,
            log_level=logging.getLevelName(self.log_level)
        )
        
    def get_log_files(self) -> Dict[str, str]:
        """Get paths to all log files"""
        files = {}
        for filename in os.listdir(self.log_dir):
            if filename.endswith(('.log', '.json')):
                files[filename] = os.path.join(self.log_dir, filename)
        return files


class JsonFileHandler(logging.Handler):
    """Custom handler for JSON structured logging"""
    
    def __init__(self, filename: str, correlation_id: str):
        super().__init__()
        self.filename = filename
        self.correlation_id = correlation_id
        
    def emit(self, record):
        """Emit a log record (called by logger)"""
        # Skip if no structured data
        if not hasattr(record, 'structured_data'):
            return
            
    def log_structured(self, level: str, message: str, data: Dict[str, Any], 
                      include_traceback: bool = False):
        """Log structured data to JSON file"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'correlation_id': self.correlation_id,
            'message': message,
            'data': data
        }
        
        if include_traceback:
            import traceback
            entry['traceback'] = traceback.format_exc()
            
        # Append to JSON file
        with open(self.filename, 'a', encoding='utf-8') as f:
            json.dump(entry, f)
            f.write('\n')


# Global logger cache
_loggers = {}


def get_logger(name: str, correlation_id: Optional[str] = None, 
               log_level: str = "INFO") -> DebugLogger:
    """Get or create a logger instance"""
    key = f"{name}_{correlation_id}" if correlation_id else name
    
    if key not in _loggers:
        _loggers[key] = DebugLogger(name, correlation_id=correlation_id, 
                                    log_level=log_level)
                                    
    return _loggers[key]