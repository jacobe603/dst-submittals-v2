"""Tag editing pipeline stage for manual correction of extracted tags"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pipeline.base import PipelineStage, PipelineContext, StageResult


class TagEditingStage(PipelineStage):
    """
    Allow manual editing of extracted tags through various interfaces.
    
    Input: tag_mapping and extraction_details from tag extraction stage
    Output: edited_tag_mapping with user corrections
    Config:
        - enabled: Whether tag editing is enabled
        - mode: 'interactive', 'file', or 'api'
        - auto_approve_high_confidence: Auto-approve tags above threshold
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("tag_editing", config)
        
        self.enabled = config.get('enabled', False)
        self.mode = config.get('mode', 'interactive')
        self.auto_approve_high_confidence = config.get('auto_approve_high_confidence', True)
        self.high_confidence_threshold = config.get('high_confidence_threshold', 0.9)
        
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that we have tag mapping from previous stage"""
        if not self.enabled:
            return True  # Skip validation if disabled
            
        tag_mapping = context.get('tag_mapping', {})
        extraction_details = context.get('extraction_details', {})
        
        if not isinstance(tag_mapping, dict):
            if self.logger:
                self.logger.error("tag_mapping must be a dictionary")
            return False
            
        if not isinstance(extraction_details, dict):
            if self.logger:
                self.logger.error("extraction_details must be a dictionary")
            return False
            
        return True
        
    def process(self, context: PipelineContext) -> StageResult:
        """Process tag editing based on configured mode"""
        if not self.enabled:
            if self.logger:
                self.logger.info("Tag editing is disabled, passing through unchanged")
            return StageResult(
                success=True,
                data={}  # Pass through existing data unchanged
            )
            
        tag_mapping = context.get('tag_mapping', {})
        extraction_details = context.get('extraction_details', {})
        
        if self.logger:
            self.logger.info(f"Starting tag editing in {self.mode} mode")
            self.logger.info(f"Found {len(tag_mapping)} extracted tags")
            
        # Prepare editing data
        editing_data = self._prepare_editing_data(tag_mapping, extraction_details)
        
        # Edit tags based on mode
        if self.mode == 'interactive':
            edited_mapping = self._interactive_edit(editing_data)
        elif self.mode == 'file':
            edited_mapping = self._file_based_edit(editing_data)
        elif self.mode == 'api':
            edited_mapping = self._api_based_edit(editing_data)
        else:
            if self.logger:
                self.logger.error(f"Unknown editing mode: {self.mode}")
            return StageResult(
                success=False,
                error=f"Unknown editing mode: {self.mode}"
            )
            
        # Log changes
        changes = self._log_changes(tag_mapping, edited_mapping)
        
        if self.logger:
            self.logger.info(f"Tag editing complete: {len(changes)} changes made")
            
        return StageResult(
            success=True,
            data={
                'tag_mapping': edited_mapping,
                'editing_changes': changes
            },
            debug_info={
                'mode': self.mode,
                'original_count': len(tag_mapping),
                'final_count': len(edited_mapping),
                'changes_made': len(changes)
            }
        )
        
    def _prepare_editing_data(self, tag_mapping: Dict[str, str], 
                            extraction_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare data for editing interface"""
        editing_data = []
        
        all_files = set(tag_mapping.keys()) | set(extraction_details.keys())
        
        for filename in all_files:
            tag = tag_mapping.get(filename)
            details = extraction_details.get(filename, {})
            
            item = {
                'filename': filename,
                'current_tag': tag,
                'confidence': details.get('confidence', 0.0),
                'extraction_method': details.get('details', {}).get('method', 'unknown'),
                'needs_review': self._needs_review(tag, details),
                'suggested_corrections': self._get_suggestions(filename, tag, details)
            }
            
            editing_data.append(item)
            
        # Sort by files that need review first, then by filename
        editing_data.sort(key=lambda x: (not x['needs_review'], x['filename']))
        
        return editing_data
        
    def _needs_review(self, tag: Optional[str], details: Dict[str, Any]) -> bool:
        """Determine if a tag needs manual review"""
        # No tag found
        if not tag:
            return True
            
        # Low confidence
        confidence = details.get('confidence', 0.0)
        if confidence < self.high_confidence_threshold:
            return True
            
        # Extraction errors
        if details.get('error'):
            return True
            
        # Auto-approve high confidence tags if enabled
        if self.auto_approve_high_confidence and confidence >= self.high_confidence_threshold:
            return False
            
        return True
        
    def _get_suggestions(self, filename: str, tag: Optional[str], 
                        details: Dict[str, Any]) -> List[str]:
        """Generate suggested corrections for a tag"""
        suggestions = []
        
        # Extract number from filename for suggestions
        number_match = re.search(r'(\d+)', filename)
        if number_match:
            number = number_match.group(1)
            
            # Remove leading zeros
            number = str(int(number))
            
            # Common tag patterns
            suggestions.extend([
                f'AHU-{number}',
                f'MAU-{number}',
                f'VAV-{number}',
                f'EF-{number}',
                f'SF-{number}'
            ])
            
        # If tag exists, suggest variations
        if tag:
            tag_match = re.match(r'([A-Z]+)-?(\d+)([A-Z]*)', tag.upper())
            if tag_match:
                prefix, number, suffix = tag_match.groups()
                
                # Suggest normalized version
                normalized = f'{prefix}-{number}{suffix}'
                if normalized != tag:
                    suggestions.insert(0, normalized)
                    
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen and suggestion != tag:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
                
        return unique_suggestions[:5]  # Limit to 5 suggestions
        
    def _interactive_edit(self, editing_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Interactive command-line tag editing"""
        edited_mapping = {}
        
        print("\n" + "="*60)
        print("TAG EDITING - Interactive Mode")
        print("="*60)
        print("Commands:")
        print("  <enter>     - Keep current tag")
        print("  <number>    - Use suggestion number")
        print("  <custom>    - Enter custom tag")
        print("  skip        - Skip this file (no tag)")
        print("  done        - Finish editing")
        print("="*60)
        
        for i, item in enumerate(editing_data):
            if not item['needs_review'] and self.auto_approve_high_confidence:
                # Auto-approve high confidence tags
                if item['current_tag']:
                    edited_mapping[item['filename']] = item['current_tag']
                continue
                
            print(f"\n[{i+1}/{len(editing_data)}] {item['filename']}")
            print(f"Current tag: {item['current_tag'] or 'None'}")
            print(f"Confidence: {item['confidence']:.2f}")
            print(f"Method: {item['extraction_method']}")
            
            if item['suggested_corrections']:
                print("Suggestions:")
                for j, suggestion in enumerate(item['suggested_corrections'], 1):
                    print(f"  {j}. {suggestion}")
                    
            while True:
                try:
                    response = input("Enter choice: ").strip()
                    
                    if response == '':
                        # Keep current tag
                        if item['current_tag']:
                            edited_mapping[item['filename']] = item['current_tag']
                        break
                        
                    elif response.lower() == 'skip':
                        # Skip this file
                        break
                        
                    elif response.lower() == 'done':
                        # Finish editing
                        print("Editing complete.")
                        return edited_mapping
                        
                    elif response.isdigit():
                        # Use suggestion
                        idx = int(response) - 1
                        if 0 <= idx < len(item['suggested_corrections']):
                            edited_mapping[item['filename']] = item['suggested_corrections'][idx]
                            print(f"Set to: {item['suggested_corrections'][idx]}")
                            break
                        else:
                            print("Invalid suggestion number.")
                            
                    else:
                        # Custom tag
                        if self._validate_tag_format(response):
                            edited_mapping[item['filename']] = response.upper()
                            print(f"Set to: {response.upper()}")
                            break
                        else:
                            print("Invalid tag format. Expected format: XXX-## (e.g., AHU-10)")
                            
                except KeyboardInterrupt:
                    print("\nEditing cancelled.")
                    break
                except EOFError:
                    print("\nEditing complete.")
                    break
                    
        return edited_mapping
        
    def _file_based_edit(self, editing_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """File-based tag editing using JSON file"""
        edit_file = 'tag_editing.json'
        
        # Create editing file if it doesn't exist
        if not os.path.exists(edit_file):
            self._create_edit_file(editing_data, edit_file)
            
            print(f"\nTag editing file created: {edit_file}")
            print("Please edit the file and run again.")
            print("Set 'edited_tag' field for each file you want to change.")
            
            # Return original mapping for now
            return {item['filename']: item['current_tag'] 
                   for item in editing_data if item['current_tag']}
                   
        # Load edited file
        try:
            with open(edit_file, 'r') as f:
                edit_data = json.load(f)
                
            edited_mapping = {}
            
            for item in edit_data:
                filename = item['filename']
                edited_tag = item.get('edited_tag', '').strip()
                
                if edited_tag:
                    if self._validate_tag_format(edited_tag):
                        edited_mapping[filename] = edited_tag.upper()
                    else:
                        if self.logger:
                            self.logger.warning(f"Invalid tag format '{edited_tag}' for {filename}")
                elif item.get('current_tag'):
                    # Keep current tag if no edit specified
                    edited_mapping[filename] = item['current_tag']
                    
            # Archive the edit file
            os.rename(edit_file, f"{edit_file}.processed")
            
            return edited_mapping
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error reading edit file: {e}")
            # Return original mapping on error
            return {item['filename']: item['current_tag'] 
                   for item in editing_data if item['current_tag']}
                   
    def _api_based_edit(self, editing_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """API-based tag editing (placeholder for web interface integration)"""
        # This would integrate with the web interface for editing
        # For now, just return original mapping
        if self.logger:
            self.logger.info("API-based editing not yet implemented, using original tags")
            
        return {item['filename']: item['current_tag'] 
               for item in editing_data if item['current_tag']}
               
    def _create_edit_file(self, editing_data: List[Dict[str, Any]], filename: str):
        """Create JSON file for editing tags"""
        edit_data = []
        
        for item in editing_data:
            edit_item = {
                'filename': item['filename'],
                'current_tag': item['current_tag'],
                'edited_tag': '',  # User fills this in
                'confidence': item['confidence'],
                'needs_review': item['needs_review'],
                'suggestions': item['suggested_corrections'],
                'notes': 'Set edited_tag to change, leave empty to keep current_tag'
            }
            edit_data.append(edit_item)
            
        with open(filename, 'w') as f:
            json.dump(edit_data, f, indent=2)
            
    def _validate_tag_format(self, tag: str) -> bool:
        """Validate tag format (e.g., AHU-10, MAU-12A)"""
        pattern = r'^[A-Z]{2,4}-\d+[A-Z]*$'
        return bool(re.match(pattern, tag.upper()))
        
    def _log_changes(self, original: Dict[str, str], edited: Dict[str, str]) -> List[Dict[str, Any]]:
        """Log and return changes made during editing"""
        changes = []
        
        all_files = set(original.keys()) | set(edited.keys())
        
        for filename in all_files:
            orig_tag = original.get(filename)
            edit_tag = edited.get(filename)
            
            if orig_tag != edit_tag:
                change = {
                    'filename': filename,
                    'original_tag': orig_tag,
                    'edited_tag': edit_tag,
                    'change_type': self._get_change_type(orig_tag, edit_tag)
                }
                changes.append(change)
                
                if self.logger:
                    self.logger.info(f"Changed {filename}: {orig_tag} -> {edit_tag}")
                    
        return changes
        
    def _get_change_type(self, original: Optional[str], edited: Optional[str]) -> str:
        """Determine the type of change made"""
        if not original and edited:
            return 'added'
        elif original and not edited:
            return 'removed'
        elif original and edited:
            return 'modified'
        else:
            return 'unchanged'