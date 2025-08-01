#!/usr/bin/env python3
"""
Custom exception classes for DST Submittals Generator
Provides domain-specific exceptions with error codes and remediation guidance
"""

from typing import Optional, Dict, Any
import os


class DSTError(Exception):
    """Base exception class for DST Submittals Generator"""
    
    def __init__(self, message: str, error_code: str = None, remediation: str = None, 
                 context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__
        self.remediation = remediation
        self.context = context or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for structured logging"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': str(self),
            'remediation': self.remediation,
            'context': self.context
        }


class ConfigurationError(DSTError):
    """Configuration-related errors"""
    
    def __init__(self, message: str, setting_name: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if setting_name:
            self.context['setting_name'] = setting_name


class PathNotFoundError(DSTError):
    """File or directory path not found"""
    
    def __init__(self, path: str, operation: str = None, **kwargs):
        message = f"Path not found: {path}"
        if operation:
            message = f"Path not found for {operation}: {path}"
            
        remediation = f"Please verify the path exists and is accessible: {path}"
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['path'] = path
        self.context['operation'] = operation


class DependencyNotFoundError(DSTError):
    """Required dependency not found"""
    
    def __init__(self, dependency: str, operation: str = None, **kwargs):
        message = f"Required dependency not found: {dependency}"
        if operation:
            message = f"Required dependency for {operation} not found: {dependency}"
            
        remediation_map = {
            'OfficeToPDF': "Download OfficeToPDF.exe and set DST_OFFICETOPDF_PATH environment variable",
            'Word': "Install Microsoft Word and ensure COM automation is enabled",
            'LibreOffice': "Install LibreOffice and ensure it's in your system PATH",
            'python-docx': "Install required Python packages: pip install -r requirements.txt"
        }
        
        remediation = remediation_map.get(dependency, f"Install or configure {dependency}")
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['dependency'] = dependency
        self.context['operation'] = operation


class TagExtractionError(DSTError):
    """Tag extraction from documents failed"""
    
    def __init__(self, filename: str, method: str = None, **kwargs):
        message = f"Failed to extract tag from document: {filename}"
        if method:
            message = f"Failed to extract tag from {filename} using {method}"
            
        remediation = (
            "Verify the document contains equipment tags (AHU-1, MAU-12, etc.) "
            "in a recognizable format. Check if file is corrupted or password protected."
        )
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['filename'] = filename
        self.context['method'] = method


class PDFConversionError(DSTError):
    """PDF conversion failed"""
    
    def __init__(self, filename: str, method: str = None, original_error: Exception = None, **kwargs):
        message = f"Failed to convert document to PDF: {filename}"
        if method:
            message = f"Failed to convert {filename} to PDF using {method}"
            
        remediation_map = {
            'officetopdf': "Check if OfficeToPDF.exe is accessible and document format is supported",
            'word_com': "Ensure Microsoft Word is properly installed and not in use by another process",
            'docx2pdf': "Verify document is not corrupted and Word is available",
            'libreoffice': "Check if LibreOffice is installed and document format is supported"
        }
        
        remediation = remediation_map.get(method, 
            "Try different conversion methods or check if document is corrupted")
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['filename'] = filename
        self.context['method'] = method
        if original_error:
            self.context['original_error'] = str(original_error)


class DocumentProcessingError(DSTError):
    """General document processing errors"""
    
    def __init__(self, operation: str, filename: str = None, **kwargs):
        message = f"Document processing failed: {operation}"
        if filename:
            message = f"Document processing failed for {filename}: {operation}"
            
        super().__init__(message, **kwargs)
        self.context['operation'] = operation
        self.context['filename'] = filename


class COMAutomationError(DSTError):
    """COM automation specific errors"""
    
    def __init__(self, operation: str, com_object: str = None, **kwargs):
        message = f"COM automation failed: {operation}"
        if com_object:
            message = f"COM automation failed for {com_object}: {operation}"
            
        remediation = (
            "Ensure Microsoft Office applications are properly installed and not in use. "
            "Try closing all Office applications and running again. "
            "If the problem persists, restart the system to reset COM registration."
        )
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['operation'] = operation
        self.context['com_object'] = com_object


class FileAccessError(DSTError):
    """File access permission or locking errors"""
    
    def __init__(self, filename: str, operation: str, **kwargs):
        message = f"File access error during {operation}: {filename}"
        
        remediation = (
            f"Check if file is not open in another application. "
            f"Verify read/write permissions for: {filename}. "
            f"Ensure the file is not locked by another process."
        )
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['filename'] = filename
        self.context['operation'] = operation


class ProcessExecutionError(DSTError):
    """External process execution errors"""
    
    def __init__(self, command: str, return_code: int = None, stderr: str = None, **kwargs):
        message = f"Process execution failed: {command}"
        if return_code is not None:
            message = f"Process execution failed with code {return_code}: {command}"
            
        remediation = (
            f"Check if the command is available in system PATH: {command.split()[0]}. "
            f"Verify file permissions and that all required dependencies are installed."
        )
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['command'] = command
        self.context['return_code'] = return_code
        self.context['stderr'] = stderr


class ValidationError(DSTError):
    """Data validation errors"""
    
    def __init__(self, field: str, value: Any, expected: str = None, **kwargs):
        message = f"Validation failed for {field}: {value}"
        if expected:
            message = f"Validation failed for {field}: expected {expected}, got {value}"
            
        super().__init__(message, **kwargs)
        self.context['field'] = field
        self.context['value'] = value
        self.context['expected'] = expected


class PipelineError(DSTError):
    """Pipeline execution errors"""
    
    def __init__(self, stage: str, operation: str = None, files_processed: int = None, **kwargs):
        message = f"Pipeline failed at stage: {stage}"
        if operation:
            message = f"Pipeline failed at stage {stage} during {operation}"
            
        super().__init__(message, **kwargs)
        self.context['stage'] = stage
        self.context['operation'] = operation
        self.context['files_processed'] = files_processed


class ResourceExhaustionError(DSTError):
    """System resource exhaustion errors"""
    
    def __init__(self, resource: str, operation: str = None, **kwargs):
        message = f"Resource exhaustion: {resource}"
        if operation:
            message = f"Resource exhaustion during {operation}: {resource}"
            
        remediation_map = {
            'memory': "Reduce batch size or close other applications to free memory",
            'disk_space': "Free up disk space or change output directory",
            'file_handles': "Reduce concurrent operations or restart the application"
        }
        
        remediation = remediation_map.get(resource, f"Free up {resource} and try again")
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['resource'] = resource
        self.context['operation'] = operation


class PDFAssemblyError(DSTError):
    """PDF assembly and final document creation errors"""
    
    def __init__(self, operation: str, filename: str = None, **kwargs):
        message = f"PDF assembly failed: {operation}"
        if filename:
            message = f"PDF assembly failed for {filename}: {operation}"
            
        remediation = (
            "Check if all required PDF files exist and are accessible. "
            "Verify sufficient disk space for final PDF creation. "
            "Ensure no other process is using the output file."
        )
        
        super().__init__(message, remediation=remediation, **kwargs)
        self.context['operation'] = operation
        self.context['filename'] = filename


def create_exception_from_error(error: Exception, context: Dict[str, Any] = None) -> DSTError:
    """Convert standard exceptions to DST exceptions with context"""
    
    context = context or {}
    
    if isinstance(error, DSTError):
        return error
    
    error_type = type(error).__name__
    error_message = str(error)
    
    # Map common exception types to DST exceptions
    if isinstance(error, FileNotFoundError):
        return PathNotFoundError(
            path=context.get('path', 'unknown'),
            operation=context.get('operation', 'file access'),
            context=context
        )
    
    elif isinstance(error, PermissionError):
        return FileAccessError(
            filename=context.get('filename', 'unknown'),
            operation=context.get('operation', 'file access'),
            context=context
        )
    
    elif isinstance(error, ImportError):
        dependency = error_message.split()[-1] if error_message else 'unknown'
        return DependencyNotFoundError(
            dependency=dependency,
            operation=context.get('operation'),
            context=context
        )
    
    elif isinstance(error, (ValueError, TypeError)):
        return ValidationError(
            field=context.get('field', 'unknown'),
            value=context.get('value', error_message),
            context=context
        )
    
    else:
        # Generic DST error for unknown exception types
        return DSTError(
            message=f"{error_type}: {error_message}",
            error_code=error_type,
            context=context
        )


if __name__ == "__main__":
    # Test the exception classes
    
    # Test basic exception
    try:
        raise PathNotFoundError("/nonexistent/path", "file conversion")
    except DSTError as e:
        print("Exception details:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {e}")
        print(f"  Remediation: {e.remediation}")
        print(f"  Context: {e.context}")
        print(f"  Dict representation: {e.to_dict()}")
    
    print("\n" + "="*50 + "\n")
    
    # Test exception conversion
    try:
        raise FileNotFoundError("Test file not found")
    except Exception as e:
        dst_error = create_exception_from_error(e, {'path': '/test/file.txt', 'operation': 'read'})
        print("Converted exception:")
        print(f"  Type: {type(dst_error).__name__}")
        print(f"  Message: {dst_error}")
        print(f"  Remediation: {dst_error.remediation}")
        print(f"  Context: {dst_error.context}")