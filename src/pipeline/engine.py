"""Pipeline execution engine"""

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base import PipelineStage, PipelineContext, StageResult
from .checkpoint import CheckpointManager


class Pipeline:
    """Manages execution of pipeline stages"""
    
    def __init__(self, stages: List[PipelineStage], config: Optional[Dict[str, Any]] = None):
        self.stages = stages
        self.config = config or {}
        self.logger = None  # Will be set by caller
        self.checkpoint_manager = CheckpointManager(
            self.config.get('checkpoint_dir', 'checkpoints')
        )
        
    def set_logger(self, logger):
        """Set logger for pipeline and all stages"""
        self.logger = logger
        for stage in self.stages:
            stage.logger = logger
            
    def run(self, initial_context: Optional[PipelineContext] = None, 
            resume_from: Optional[str] = None) -> PipelineContext:
        """
        Execute the pipeline.
        
        Args:
            initial_context: Starting context (optional)
            resume_from: Stage name to resume from (optional)
            
        Returns:
            Final pipeline context with all results
        """
        # Create or restore context
        if resume_from:
            context = self._resume_from_checkpoint(resume_from)
            if not context:
                context = initial_context or PipelineContext()
        else:
            context = initial_context or PipelineContext()
            
        # Log pipeline start
        if self.logger:
            self.logger.info(f"Starting pipeline run: {context.correlation_id}")
            self.logger.info(f"Stages: {[s.name for s in self.stages]}")
            
        # Find starting point
        start_index = 0
        if resume_from:
            for i, stage in enumerate(self.stages):
                if stage.name == resume_from:
                    start_index = i
                    break
                    
        # Execute stages
        for i in range(start_index, len(self.stages)):
            stage = self.stages[i]
            
            # Check if we should skip this stage
            if self._should_skip_stage(stage, context):
                if self.logger:
                    self.logger.info(f"Skipping stage: {stage.name}")
                continue
                
            # Run stage
            if self.logger:
                self.logger.info(f"Executing stage {i+1}/{len(self.stages)}: {stage.name}")
                
            result = stage.run(context)
            
            # Save checkpoint after successful stage
            if result.success and self.config.get('save_checkpoints', True):
                self._save_checkpoint(context, stage.name)
                
            # Handle stage failure
            if not result.success:
                if self.logger:
                    self.logger.error(
                        f"Pipeline failed at stage {stage.name}: {result.error}"
                    )
                    
                # Check if we should continue on failure
                if not self.config.get('continue_on_failure', False):
                    break
                    
        # Log pipeline completion
        if self.logger:
            success_count = sum(
                1 for r in context._stage_results.values() if r.success
            )
            self.logger.info(
                f"Pipeline completed: {success_count}/{len(self.stages)} stages succeeded"
            )
            
        return context
        
    def _should_skip_stage(self, stage: PipelineStage, context: PipelineContext) -> bool:
        """Check if a stage should be skipped"""
        # Check if stage is disabled
        if self.config.get(f'disable_{stage.name}', False):
            return True
            
        # Check if stage has already been run (when resuming)
        if context.get_stage_result(stage.name):
            return True
            
        return False
        
    def _save_checkpoint(self, context: PipelineContext, stage_name: str) -> None:
        """Save checkpoint after successful stage"""
        try:
            checkpoint_path = self.checkpoint_manager.save(
                context, stage_name, context.correlation_id
            )
            if self.logger:
                self.logger.debug(f"Saved checkpoint: {checkpoint_path}")
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to save checkpoint: {e}")
                
    def _resume_from_checkpoint(self, stage_name: str) -> Optional[PipelineContext]:
        """Resume from a saved checkpoint"""
        try:
            # Find latest checkpoint for the stage
            checkpoint_path = self.checkpoint_manager.find_latest(stage_name)
            if not checkpoint_path:
                if self.logger:
                    self.logger.warning(f"No checkpoint found for stage: {stage_name}")
                return None
                
            # Load checkpoint
            context = self.checkpoint_manager.load(checkpoint_path)
            if self.logger:
                self.logger.info(f"Resumed from checkpoint: {checkpoint_path}")
                
            return context
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to resume from checkpoint: {e}")
            return None
            
    def get_stage_names(self) -> List[str]:
        """Get list of stage names"""
        return [stage.name for stage in self.stages]
        
    def get_stage(self, name: str) -> Optional[PipelineStage]:
        """Get stage by name"""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None