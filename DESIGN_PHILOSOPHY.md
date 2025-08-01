# DST Submittals Generator - Design Philosophy

## Core Principles

### 1. Simple Over Clever
- Each component does ONE thing well
- Avoid premature optimization
- Clear code > clever code
- If it takes more than 5 minutes to understand, it's too complex

### 2. Debuggability First
- Every operation must be traceable
- Detailed logging at every decision point
- Clear error messages that explain WHAT failed and WHY
- Save intermediate results for inspection

### 3. Modular Pipeline Architecture
- Each stage is independent
- Stages communicate through well-defined interfaces
- Failed stages can be retried without reprocessing everything
- New features = new stages (not modifications to existing ones)

## Pipeline Stage Design

### Anatomy of a Pipeline Stage

```python
class YourNewStage(PipelineStage):
    """
    One sentence describing what this stage does.
    
    Input: What it expects from previous stage
    Output: What it provides to next stage
    Config: What options control its behavior
    """
    
    def __init__(self, config: dict):
        super().__init__("YourStageName", config)
        # Initialize any stage-specific settings
        
    def validate_input(self, context: PipelineContext) -> bool:
        """Check if we have what we need to run"""
        # Return True if input is valid, False otherwise
        
    def process(self, context: PipelineContext) -> StageResult:
        """Do the actual work"""
        # 1. Get input from context
        # 2. Process it
        # 3. Return results
        
    def validate_output(self, result: StageResult) -> bool:
        """Verify our output is correct"""
        # Return True if output is valid, False otherwise
```

### Stage Communication

Stages communicate through a shared context:

```python
context = {
    'config': {},          # Global configuration
    'files': [],           # Input files
    'tag_mapping': {},     # File -> Tag mapping
    'classifications': {}, # File -> Type mapping
    'converted_pdfs': {},  # Original -> PDF mapping
    'debug_info': {}       # Stage-specific debug data
}
```

## Adding New Features

### Step 1: Define the Stage
1. What input does it need?
2. What output does it produce?
3. What can go wrong?
4. What options should be configurable?

### Step 2: Create the Stage File
```
src/stages/your_feature.py
```

### Step 3: Implement Required Methods
- `validate_input()` - What do we need?
- `process()` - Do the work
- `validate_output()` - Did we succeed?

### Step 4: Add to Pipeline Configuration
```python
# In pipeline_config.py
PIPELINE_STAGES = [
    'validation',
    'tag_extraction', 
    'your_feature',  # Add your stage in the right order
    'classification',
    'conversion',
    'assembly'
]
```

### Step 5: Add Tests
```python
# In tests/test_your_feature.py
def test_your_feature_happy_path():
    # Test normal operation
    
def test_your_feature_edge_cases():
    # Test boundary conditions
    
def test_your_feature_error_handling():
    # Test failure modes
```

## Example: Adding Tag Editing Feature

```python
class TagEditingStage(PipelineStage):
    """
    Allows manual editing of extracted tags.
    
    Input: tag_mapping from extraction stage
    Output: edited_tag_mapping with user corrections
    Config: edit_mode (interactive/file/api)
    """
    
    def __init__(self, config: dict):
        super().__init__("tag_editing", config)
        self.edit_mode = config.get('edit_mode', 'interactive')
        
    def process(self, context: PipelineContext) -> StageResult:
        tag_mapping = context.get('tag_mapping', {})
        
        if self.edit_mode == 'interactive':
            edited_mapping = self.interactive_edit(tag_mapping)
        elif self.edit_mode == 'file':
            edited_mapping = self.file_based_edit(tag_mapping)
        elif self.edit_mode == 'api':
            edited_mapping = self.api_based_edit(tag_mapping)
            
        return StageResult(
            success=True,
            data={'tag_mapping': edited_mapping}
        )
```

## Configuration Philosophy

### Environment Variables
- Use for deployment-specific settings (paths, credentials)
- Always provide sensible defaults
- Document in .env.example

### Feature Flags
```python
# Good: Clear on/off switches
USE_PIPELINE_MODE = False
ENABLE_TAG_EDITING = True
TAG_EXTRACTION_MODE = 'content'  # 'content' or 'filename'

# Bad: Complex nested conditions
if config.get('advanced', {}).get('features', {}).get('experimental'):
    # Too deep!
```

### Stage-Specific Config
```python
# In config.py
STAGE_CONFIG = {
    'tag_extraction': {
        'mode': 'content',  # or 'filename'
        'patterns': [...],
        'confidence_threshold': 0.8
    },
    'tag_editing': {
        'enabled': True,
        'mode': 'interactive'
    }
}
```

## Error Handling Philosophy

### Fail Fast, Fail Clear
```python
# Good: Clear error with context
if not os.path.exists(file_path):
    raise FileNotFoundError(
        f"Cannot find input file: {file_path}\n"
        f"Searched in: {os.path.dirname(file_path)}\n"
        f"Available files: {os.listdir(os.path.dirname(file_path))[:5]}"
    )

# Bad: Generic error
if not os.path.exists(file_path):
    raise Exception("File error")
```

### Graceful Degradation
- If OfficeToPDF fails, try Word COM
- If tag extraction fails for one file, continue with others
- Always provide partial results when possible

## Testing Philosophy

### Test Levels
1. **Unit Tests**: Each stage in isolation
2. **Integration Tests**: Multiple stages together
3. **End-to-End Tests**: Full pipeline runs
4. **Regression Tests**: Ensure fixes stay fixed

### Test Data
```
tests/fixtures/
├── simple/        # Basic test cases
├── edge_cases/    # Weird filenames, empty files, etc.
├── real_world/    # Actual customer files (anonymized)
└── expected/      # Expected outputs for comparison
```

## Debugging Tools

### Debug Mode
```bash
# Run with maximum verbosity
python dst_submittals.py --debug documents/

# Creates detailed logs in:
# debug_logs/2024-01-15_14-30-00_a1b2c3/
# ├── pipeline.log      # Overall flow
# ├── validation.log    # Input validation details
# ├── extraction.log    # Tag extraction details
# ├── conversion.log    # PDF conversion details
# └── checkpoint.json   # Current state
```

### Interactive Debugging
```python
# Add breakpoints in stages
if self.config.get('debug_break'):
    import pdb; pdb.set_trace()
```

## Performance Considerations

### Parallel When Possible
- PDF conversions can run in parallel
- Tag extraction can process multiple files concurrently
- But respect Office COM single-threading requirements

### Cache Expensive Operations
- Store extracted tags in checkpoint files
- Reuse PDF conversions if source hasn't changed
- Cache regex compilations

## Version Migration

### Adding New Stages
1. New stages default to disabled
2. Run in parallel with old code
3. Compare outputs
4. Enable when confident

### Changing Stage Behavior
1. Use version flags in config
2. Support old behavior during transition
3. Log when using deprecated features
4. Clean up after migration period

## Summary

The key to maintaining this codebase is:
1. **Keep stages small and focused**
2. **Log everything that matters**
3. **Make failures obvious**
4. **Test each piece independently**
5. **Document WHY, not just WHAT**

When in doubt, ask:
- Can I test this in isolation?
- Will I understand this in 6 months?
- Can I debug this from logs alone?
- Is this the simplest solution?

If any answer is "no", refactor until they're all "yes".