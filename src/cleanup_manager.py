#!/usr/bin/env python3
"""
Cleanup Manager for DST Submittals Generator

Handles automatic cleanup of generated PDFs, temporary files, and directories
to prevent disk space accumulation during operation.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import threading

try:
    from .logger import get_logger
    from .config import Config
except ImportError:
    from logger import get_logger
    from config import Config

logger = get_logger('cleanup_manager')


class CleanupManager:
    """
    Manages cleanup of generated PDFs, temporary files, and directories
    
    Features:
    - Automatic cleanup of web_outputs directory based on age/count limits
    - Cleanup of orphaned temporary directories
    - Background periodic cleanup task
    - Disk usage monitoring and logging
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        
        # Cleanup configuration with defaults
        self.max_output_files = int(os.environ.get('DST_MAX_OUTPUT_FILES', '10'))
        self.retention_days = int(os.environ.get('DST_OUTPUT_RETENTION_DAYS', '7'))
        self.cleanup_on_startup = os.environ.get('DST_CLEANUP_ON_STARTUP', 'true').lower() == 'true'
        self.periodic_cleanup_hours = int(os.environ.get('DST_PERIODIC_CLEANUP_HOURS', '24'))
        
        # Directories to manage
        self.web_outputs_dir = Path('web_outputs')
        self.temp_base_dir = Path(tempfile.gettempdir())
        
        # Background cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        
        logger.info(f"CleanupManager initialized with max_files={self.max_output_files}, "
                   f"retention_days={self.retention_days}, "
                   f"cleanup_on_startup={self.cleanup_on_startup}")
    
    def get_disk_usage(self, path: Path) -> Dict[str, Any]:
        """
        Get disk usage information for a directory
        
        Args:
            path: Directory path to check
            
        Returns:
            Dictionary with usage information
        """
        try:
            if not path.exists():
                return {'exists': False, 'total_bytes': 0, 'file_count': 0}
            
            total_size = 0
            file_count = 0
            
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except (OSError, FileNotFoundError):
                        continue
            
            return {
                'exists': True,
                'total_bytes': total_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'path': str(path)
            }
        except Exception as e:
            logger.warning(f"Failed to get disk usage for {path}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def cleanup_web_outputs(self) -> Dict[str, Any]:
        """
        Clean up the web_outputs directory based on retention policy
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            if not self.web_outputs_dir.exists():
                logger.debug(f"Web outputs directory does not exist: {self.web_outputs_dir}")
                return {'success': True, 'removed_files': 0, 'reason': 'directory_not_exists'}
            
            # Get all PDF files with their modification times
            pdf_files = []
            for pdf_path in self.web_outputs_dir.glob('*.pdf'):
                try:
                    stat = pdf_path.stat()
                    pdf_files.append({
                        'path': pdf_path,
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'age_days': (time.time() - stat.st_mtime) / (24 * 3600)
                    })
                except (OSError, FileNotFoundError):
                    continue
            
            if not pdf_files:
                logger.debug("No PDF files found in web outputs directory")
                return {'success': True, 'removed_files': 0, 'reason': 'no_files'}
            
            # Sort by modification time (newest first)
            pdf_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            removed_files = []
            total_size_removed = 0
            
            # Remove files based on count limit
            if len(pdf_files) > self.max_output_files:
                files_to_remove = pdf_files[self.max_output_files:]
                for file_info in files_to_remove:
                    try:
                        file_info['path'].unlink()
                        removed_files.append({
                            'filename': file_info['path'].name,
                            'size': file_info['size'],
                            'age_days': round(file_info['age_days'], 1),
                            'reason': 'count_limit'
                        })
                        total_size_removed += file_info['size']
                        logger.info(f"Removed old PDF (count limit): {file_info['path'].name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_info['path']}: {e}")
            
            # Remove files based on age limit
            cutoff_time = time.time() - (self.retention_days * 24 * 3600)
            for file_info in pdf_files:
                if file_info['mtime'] < cutoff_time and file_info['path'].exists():
                    try:
                        file_info['path'].unlink()
                        # Check if already in removed_files to avoid duplicates
                        if not any(rf['filename'] == file_info['path'].name for rf in removed_files):
                            removed_files.append({
                                'filename': file_info['path'].name,
                                'size': file_info['size'],
                                'age_days': round(file_info['age_days'], 1),
                                'reason': 'age_limit'
                            })
                            total_size_removed += file_info['size']
                        logger.info(f"Removed old PDF (age limit): {file_info['path'].name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_info['path']}: {e}")
            
            result = {
                'success': True,
                'removed_files': len(removed_files),
                'total_size_removed': total_size_removed,
                'total_size_removed_mb': round(total_size_removed / (1024 * 1024), 2),
                'remaining_files': len(pdf_files) - len(removed_files),
                'files_removed': removed_files
            }
            
            if removed_files:
                logger.info(f"Web outputs cleanup completed: removed {len(removed_files)} files "
                           f"({result['total_size_removed_mb']} MB)")
            else:
                logger.debug("Web outputs cleanup: no files needed removal")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup web outputs: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_temp_directories(self) -> Dict[str, Any]:
        """
        Clean up orphaned temporary directories created by the application
        
        Returns:
            Dictionary with cleanup results
        """
        try:
            temp_patterns = ['dst_web_*', 'dst_tags_*', 'dst_extract_*']
            removed_dirs = []
            total_size_removed = 0
            
            # Look for temp directories matching our patterns
            for pattern in temp_patterns:
                for temp_dir in self.temp_base_dir.glob(pattern):
                    if not temp_dir.is_dir():
                        continue
                    
                    try:
                        # Check if directory is old enough to remove (older than 1 hour)
                        stat = temp_dir.stat()
                        age_hours = (time.time() - stat.st_mtime) / 3600
                        
                        if age_hours > 1:  # Remove directories older than 1 hour
                            # Calculate size before removal
                            dir_size = sum(f.stat().st_size for f in temp_dir.rglob('*') if f.is_file())
                            
                            shutil.rmtree(temp_dir)
                            removed_dirs.append({
                                'dirname': temp_dir.name,
                                'size': dir_size,
                                'age_hours': round(age_hours, 1)
                            })
                            total_size_removed += dir_size
                            logger.info(f"Removed temp directory: {temp_dir.name} (age: {age_hours:.1f}h)")
                            
                    except Exception as e:
                        logger.warning(f"Failed to remove temp directory {temp_dir}: {e}")
            
            result = {
                'success': True,
                'removed_directories': len(removed_dirs),
                'total_size_removed': total_size_removed,
                'total_size_removed_mb': round(total_size_removed / (1024 * 1024), 2),
                'directories_removed': removed_dirs
            }
            
            if removed_dirs:
                logger.info(f"Temp directories cleanup completed: removed {len(removed_dirs)} directories "
                           f"({result['total_size_removed_mb']} MB)")
            else:
                logger.debug("Temp directories cleanup: no directories needed removal")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp directories: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_full_cleanup(self) -> Dict[str, Any]:
        """
        Run complete cleanup of all managed areas
        
        Returns:
            Dictionary with combined cleanup results
        """
        logger.info("Starting full cleanup operation...")
        
        web_outputs_result = self.cleanup_web_outputs()
        temp_dirs_result = self.cleanup_temp_directories()
        
        # Calculate totals
        total_files_removed = web_outputs_result.get('removed_files', 0)
        total_dirs_removed = temp_dirs_result.get('removed_directories', 0)
        total_size_removed = (web_outputs_result.get('total_size_removed', 0) + 
                            temp_dirs_result.get('total_size_removed', 0))
        
        result = {
            'success': web_outputs_result.get('success', False) and temp_dirs_result.get('success', False),
            'web_outputs': web_outputs_result,
            'temp_directories': temp_dirs_result,
            'summary': {
                'total_files_removed': total_files_removed,
                'total_directories_removed': total_dirs_removed,
                'total_size_removed': total_size_removed,
                'total_size_removed_mb': round(total_size_removed / (1024 * 1024), 2)
            }
        }
        
        logger.info(f"Full cleanup completed: removed {total_files_removed} files, "
                   f"{total_dirs_removed} directories ({result['summary']['total_size_removed_mb']} MB)")
        
        return result
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """
        Get current status of managed directories and cleanup configuration
        
        Returns:
            Dictionary with status information
        """
        web_outputs_usage = self.get_disk_usage(self.web_outputs_dir)
        
        return {
            'configuration': {
                'max_output_files': self.max_output_files,
                'retention_days': self.retention_days,
                'cleanup_on_startup': self.cleanup_on_startup,
                'periodic_cleanup_hours': self.periodic_cleanup_hours
            },
            'web_outputs': web_outputs_usage,
            'periodic_cleanup_running': self._cleanup_thread is not None and self._cleanup_thread.is_alive()
        }
    
    def start_periodic_cleanup(self):
        """Start background periodic cleanup task"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.info("Periodic cleanup already running")
            return
        
        if self.periodic_cleanup_hours <= 0:
            logger.info("Periodic cleanup disabled (interval <= 0)")
            return
        
        def cleanup_worker():
            logger.info(f"Starting periodic cleanup task (every {self.periodic_cleanup_hours} hours)")
            
            while not self._stop_cleanup.wait(self.periodic_cleanup_hours * 3600):
                try:
                    logger.info("Running scheduled cleanup...")
                    self.run_full_cleanup()
                except Exception as e:
                    logger.error(f"Periodic cleanup failed: {e}")
            
            logger.info("Periodic cleanup task stopped")
        
        self._cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Periodic cleanup task started")
    
    def stop_periodic_cleanup(self):
        """Stop background periodic cleanup task"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.info("Stopping periodic cleanup task...")
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            logger.info("Periodic cleanup task stopped")
        else:
            logger.debug("Periodic cleanup task not running")
    
    def startup_cleanup(self):
        """Run cleanup operations at application startup"""
        if not self.cleanup_on_startup:
            logger.info("Startup cleanup disabled")
            return
        
        logger.info("Running startup cleanup...")
        result = self.run_full_cleanup()
        
        if result['success']:
            summary = result['summary']
            if summary['total_files_removed'] > 0 or summary['total_directories_removed'] > 0:
                logger.info(f"Startup cleanup completed: removed {summary['total_files_removed']} files, "
                           f"{summary['total_directories_removed']} directories "
                           f"({summary['total_size_removed_mb']} MB)")
            else:
                logger.info("Startup cleanup completed: no cleanup needed")
        else:
            logger.warning("Startup cleanup completed with errors")
        
        return result


def test_cleanup_manager():
    """Test function for cleanup manager"""
    cleanup_manager = CleanupManager()
    
    print("Cleanup Manager Configuration:")
    status = cleanup_manager.get_cleanup_status()
    print(f"  Max output files: {status['configuration']['max_output_files']}")
    print(f"  Retention days: {status['configuration']['retention_days']}")
    print(f"  Cleanup on startup: {status['configuration']['cleanup_on_startup']}")
    
    print("\nWeb Outputs Status:")
    web_outputs = status['web_outputs']
    if web_outputs['exists']:
        print(f"  Files: {web_outputs['file_count']}")
        print(f"  Size: {web_outputs['total_mb']} MB")
    else:
        print("  Directory does not exist")
    
    print("\nRunning test cleanup...")
    result = cleanup_manager.run_full_cleanup()
    print(f"Cleanup result: {result['success']}")
    
    if result['success']:
        summary = result['summary']
        print(f"  Files removed: {summary['total_files_removed']}")
        print(f"  Directories removed: {summary['total_directories_removed']}")
        print(f"  Size removed: {summary['total_size_removed_mb']} MB")


if __name__ == '__main__':
    test_cleanup_manager()