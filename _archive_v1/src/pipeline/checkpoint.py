"""Checkpoint management for pipeline resumption"""

import os
import json
import glob
from datetime import datetime
from typing import Optional

from .base import PipelineContext, StageResult


class CheckpointManager:
    """Manages saving and loading of pipeline checkpoints"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
    def save(self, context: PipelineContext, stage_name: str, 
             correlation_id: str) -> str:
        """
        Save a checkpoint after successful stage completion.
        
        Returns:
            Path to saved checkpoint file
        """
        # Create checkpoint data
        checkpoint = {
            'stage_name': stage_name,
            'correlation_id': correlation_id,
            'timestamp': datetime.now().isoformat(),
            'context': context.to_dict()
        }
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"checkpoint_{correlation_id}_{stage_name}_{timestamp}.json"
        filepath = os.path.join(self.checkpoint_dir, filename)
        
        # Save checkpoint
        with open(filepath, 'w') as f:
            json.dump(checkpoint, f, indent=2)
            
        # Clean up old checkpoints
        self._cleanup_old_checkpoints(correlation_id)
        
        return filepath
        
    def load(self, checkpoint_path: str) -> PipelineContext:
        """Load a checkpoint from file"""
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
            
        # Reconstruct context
        context = PipelineContext()
        context._data = checkpoint['context']['data']
        context._metadata = checkpoint['context']['metadata']
        
        # Reconstruct stage results
        for stage_name, result_dict in checkpoint['context']['stage_results'].items():
            result = StageResult(
                success=result_dict['success'],
                data=result_dict.get('data', {}),
                error=result_dict.get('error'),
                warnings=result_dict.get('warnings', []),
                debug_info=result_dict.get('debug_info', {}),
                duration=result_dict.get('duration', 0.0)
            )
            context._stage_results[stage_name] = result
            
        return context
        
    def find_latest(self, stage_name: Optional[str] = None, 
                    correlation_id: Optional[str] = None) -> Optional[str]:
        """
        Find the most recent checkpoint matching criteria.
        
        Args:
            stage_name: Filter by stage name
            correlation_id: Filter by correlation ID
            
        Returns:
            Path to latest checkpoint or None
        """
        pattern = "checkpoint_"
        if correlation_id:
            pattern += f"{correlation_id}_"
        if stage_name:
            pattern += f"{stage_name}_"
        pattern += "*.json"
        
        checkpoint_files = glob.glob(
            os.path.join(self.checkpoint_dir, pattern)
        )
        
        if not checkpoint_files:
            return None
            
        # Sort by modification time and return latest
        checkpoint_files.sort(key=os.path.getmtime, reverse=True)
        return checkpoint_files[0]
        
    def list_checkpoints(self, correlation_id: Optional[str] = None) -> list:
        """List all checkpoints, optionally filtered by correlation ID"""
        pattern = "checkpoint_"
        if correlation_id:
            pattern += f"{correlation_id}_"
        pattern += "*.json"
        
        checkpoint_files = glob.glob(
            os.path.join(self.checkpoint_dir, pattern)
        )
        
        checkpoints = []
        for filepath in checkpoint_files:
            with open(filepath, 'r') as f:
                checkpoint = json.load(f)
                checkpoints.append({
                    'filepath': filepath,
                    'stage_name': checkpoint['stage_name'],
                    'correlation_id': checkpoint['correlation_id'],
                    'timestamp': checkpoint['timestamp']
                })
                
        # Sort by timestamp
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        return checkpoints
        
    def _cleanup_old_checkpoints(self, correlation_id: str, keep_last: int = 3):
        """Clean up old checkpoints for a correlation ID"""
        checkpoints = self.list_checkpoints(correlation_id)
        
        # Group by stage
        stage_checkpoints = {}
        for cp in checkpoints:
            stage = cp['stage_name']
            if stage not in stage_checkpoints:
                stage_checkpoints[stage] = []
            stage_checkpoints[stage].append(cp['filepath'])
            
        # Keep only the last N checkpoints per stage
        for stage, filepaths in stage_checkpoints.items():
            for filepath in filepaths[keep_last:]:
                try:
                    os.remove(filepath)
                except Exception:
                    pass  # Ignore errors during cleanup
                    
    def cleanup_all(self, days_to_keep: int = 7):
        """Clean up all checkpoints older than specified days"""
        import time
        
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for filepath in glob.glob(os.path.join(self.checkpoint_dir, "checkpoint_*.json")):
            try:
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
            except Exception:
                pass  # Ignore errors during cleanup