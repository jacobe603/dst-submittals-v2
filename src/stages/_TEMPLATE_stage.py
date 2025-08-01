"""Template for creating new pipeline stages"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pipeline.base import PipelineStage, PipelineContext, StageResult


class TemplateStage(PipelineStage):
    """
    TEMPLATE: One-line description of what this stage does.
    
    Input: What this stage expects from the context (be specific)
    Output: What this stage adds to the context (be specific)  
    Config: What configuration options control behavior
    
    Example:
        Input: List of PDF files in context['converted_pdfs']
        Output: Dict mapping files to quality scores in context['quality_scores']
        Config: quality_threshold (float), enable_ocr (bool)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("template_stage", config)
        
        # Extract configuration with defaults
        self.some_setting = config.get('some_setting', 'default_value')
        self.enabled = config.get('enabled', True)
        
    def validate_input(self, context: PipelineContext) -> bool:
        """
        Validate that required input is present in context.
        
        Return True if input is valid, False otherwise.
        Log specific errors to help with debugging.
        """
        # Check if we're enabled
        if not self.enabled:
            return True  # Skip validation if disabled
            
        # Check for required input
        required_data = context.get('required_key')
        if not required_data:
            if self.logger:
                self.logger.error("Missing required input: required_key")
            return False
            
        # Validate input format
        if not isinstance(required_data, (list, dict)):
            if self.logger:
                self.logger.error(f"Invalid input type: expected list/dict, got {type(required_data)}")
            return False
            
        return True
        
    def process(self, context: PipelineContext) -> StageResult:
        """
        Process the stage logic.
        
        This is where the actual work happens. Follow this pattern:
        1. Get input from context
        2. Process it with detailed logging
        3. Return results with proper error handling
        """
        # Skip processing if disabled
        if not self.enabled:
            if self.logger:
                self.logger.info("Template stage is disabled, skipping")
            return StageResult(success=True, data={})
            
        # Get input data
        input_data = context.get('required_key', [])
        
        if self.logger:
            self.logger.info(f"Processing {len(input_data)} items")
            
        try:
            # Do the actual processing
            results = {}
            processed_count = 0
            error_count = 0
            
            for item in input_data:
                try:
                    # Process individual item
                    result = self._process_single_item(item)
                    results[str(item)] = result
                    processed_count += 1
                    
                    if self.logger:
                        self.logger.debug(f"Processed item: {item}")
                        
                except Exception as e:
                    error_count += 1
                    if self.logger:
                        self.logger.error(f"Error processing item {item}: {e}")
                    # Continue processing other items
                    
            # Log summary
            if self.logger:
                self.logger.info(
                    f"Template stage complete: {processed_count} processed, {error_count} errors"
                )
                
            return StageResult(
                success=True,
                data={
                    'template_results': results,
                    'processed_count': processed_count
                },
                warnings=[f"{error_count} items failed processing"] if error_count > 0 else [],
                debug_info={
                    'setting_used': self.some_setting,
                    'total_items': len(input_data),
                    'success_rate': processed_count / len(input_data) if input_data else 1.0
                }
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Template stage failed: {str(e)}"
            if self.logger:
                self.logger.exception(error_msg)
                
            return StageResult(
                success=False,
                error=error_msg,
                debug_info={'setting_used': self.some_setting}
            )
            
    def _process_single_item(self, item) -> Any:
        """
        Process a single item (helper method).
        
        Break complex processing into smaller, testable methods.
        """
        # Implement your processing logic here
        # This is just an example
        if isinstance(item, str):
            return item.upper()
        else:
            return str(item)
            
    def validate_output(self, result: StageResult) -> bool:
        """
        Validate that the stage produced valid output.
        
        Return True if output is valid, False otherwise.
        This helps catch bugs early.
        """
        if not result.success:
            return True  # Let errors be handled upstream
            
        # Check output format
        template_results = result.data.get('template_results', {})
        if not isinstance(template_results, dict):
            if self.logger:
                self.logger.error("template_results must be a dictionary")
            return False
            
        # Add more specific validation as needed
        return True
        
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about this stage.
        
        Useful for troubleshooting and monitoring.
        """
        return {
            'name': self.name,
            'config': self.config,
            'enabled': self.enabled,
            'some_setting': self.some_setting
        }


# Example of how to create a stage that extends the template
class ExampleValidationStage(TemplateStage):
    """Example: Validate file formats and sizes"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = "file_validation"  # Override name
        self.max_file_size = config.get('max_file_size', 50 * 1024 * 1024)  # 50MB
        self.allowed_extensions = config.get('allowed_extensions', ['.doc', '.docx', '.pdf'])
        
    def validate_input(self, context: PipelineContext) -> bool:
        """Check for file list"""
        files = context.get('files', [])
        if not files:
            if self.logger:
                self.logger.error("No files to validate")
            return False
        return True
        
    def _process_single_item(self, filepath: str) -> Dict[str, Any]:
        """Validate a single file"""
        result = {
            'valid': True,
            'size': 0,
            'extension': '',
            'errors': []
        }
        
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                result['valid'] = False
                result['errors'].append('File not found')
                return result
                
            # Check file size
            size = os.path.getsize(filepath)
            result['size'] = size
            
            if size > self.max_file_size:
                result['valid'] = False
                result['errors'].append(f'File too large: {size} bytes')
                
            # Check extension
            extension = Path(filepath).suffix.lower()
            result['extension'] = extension
            
            if extension not in self.allowed_extensions:
                result['valid'] = False
                result['errors'].append(f'Invalid extension: {extension}')
                
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f'Validation error: {str(e)}')
            
        return result


# Usage example:
if __name__ == "__main__":
    # Example of how to test a stage
    from pipeline.base import PipelineContext
    
    # Create test context
    context = PipelineContext({
        'files': ['test1.docx', 'test2.pdf', 'test3.txt']
    })
    
    # Create and run stage
    stage = ExampleValidationStage({
        'max_file_size': 10 * 1024 * 1024,  # 10MB
        'allowed_extensions': ['.docx', '.pdf']
    })
    
    result = stage.run(context)
    print(f"Stage result: {result.success}")
    print(f"Data: {result.data}")
    print(f"Errors: {result.error}")
    print(f"Warnings: {result.warnings}")