"""Base classes for pipeline stages"""

import os
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class StageResult:
    """Result from a pipeline stage execution"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'warnings': self.warnings,
            'debug_info': self.debug_info,
            'duration': self.duration
        }


class PipelineContext:
    """Shared context passed between pipeline stages"""
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self._data = initial_data or {}
        self._stage_results = {}
        self._metadata = {
            'start_time': datetime.now().isoformat(),
            'correlation_id': self._generate_correlation_id()
        }
        
    def _generate_correlation_id(self) -> str:
        """Generate unique ID for this pipeline run"""
        import uuid
        return str(uuid.uuid4())[:8]
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from context"""
        return self._data.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set value in context"""
        self._data[key] = value
        
    def update(self, data: Dict[str, Any]) -> None:
        """Update context with multiple values"""
        self._data.update(data)
        
    def add_stage_result(self, stage_name: str, result: StageResult) -> None:
        """Store result from a stage"""
        self._stage_results[stage_name] = result
        
    def get_stage_result(self, stage_name: str) -> Optional[StageResult]:
        """Get result from a previous stage"""
        return self._stage_results.get(stage_name)
        
    @property
    def correlation_id(self) -> str:
        """Get correlation ID for this pipeline run"""
        return self._metadata['correlation_id']
        
    def to_dict(self) -> dict:
        """Convert context to dictionary for serialization"""
        return {
            'data': self._data,
            'stage_results': {k: v.to_dict() for k, v in self._stage_results.items()},
            'metadata': self._metadata
        }


class PipelineStage(ABC):
    """Base class for all pipeline stages"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = None  # Will be set by pipeline
        
    def run(self, context: PipelineContext) -> StageResult:
        """Execute this stage with timing and error handling"""
        start_time = time.time()
        
        try:
            # Log stage start
            if self.logger:
                self.logger.info(f"Starting stage: {self.name}")
                self.logger.debug(f"Stage config: {self.config}")
            
            # Validate input
            if not self.validate_input(context):
                error_msg = f"Invalid input for stage {self.name}"
                if self.logger:
                    self.logger.error(error_msg)
                return StageResult(success=False, error=error_msg)
            
            # Process
            result = self.process(context)
            
            # Update context with results
            if result.success and result.data:
                context.update(result.data)
            
            # Validate output
            if result.success and not self.validate_output(result):
                error_msg = f"Invalid output from stage {self.name}"
                if self.logger:
                    self.logger.error(error_msg)
                result.success = False
                result.error = error_msg
            
            # Log completion
            if self.logger:
                if result.success:
                    self.logger.info(f"Stage {self.name} completed successfully")
                else:
                    self.logger.error(f"Stage {self.name} failed: {result.error}")
                    
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Stage {self.name} crashed: {str(e)}"
            if self.logger:
                self.logger.exception(error_msg)
            result = StageResult(success=False, error=error_msg)
            
        # Record duration
        result.duration = time.time() - start_time
        
        # Store result in context
        context.add_stage_result(self.name, result)
        
        return result
    
    def validate_input(self, context: PipelineContext) -> bool:
        """
        Validate that required input is present in context.
        Override in subclasses to add specific validation.
        """
        return True
        
    @abstractmethod
    def process(self, context: PipelineContext) -> StageResult:
        """
        Process the stage logic.
        Must be implemented by subclasses.
        """
        pass
        
    def validate_output(self, result: StageResult) -> bool:
        """
        Validate that the stage produced valid output.
        Override in subclasses to add specific validation.
        """
        return True
        
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about this stage.
        Override to provide stage-specific debug data.
        """
        return {
            'name': self.name,
            'config': self.config
        }