# DST Submittals Generator - Pipeline Architecture

## Overview

The DST Submittals Generator now features a modular pipeline architecture that makes development, debugging, and maintenance much easier. This document explains how to use the new system.

## Quick Start

### Testing the Pipeline

```bash
# Test the new pipeline architecture
python test_pipeline.py

# Run individual stage tests
python -m unittest tests.test_tag_extraction -v
```

### Using Pipeline Mode

```bash
# Enable pipeline mode (disabled by default)
set DST_USE_PIPELINE_MODE=true

# Configure tag extraction mode
set DST_TAG_EXTRACTION_MODE=filename  # or 'content'

# Enable tag editing
set DST_ENABLE_TAG_EDITING=true
set DST_TAG_EDIT_MODE=interactive     # or 'file' or 'api'

# Run with pipeline
python dst_submittals.py "documents/" --verbose
```

## Architecture

### Pipeline Flow

```
Input Files → [Validation] → [Tag Extraction] → [Tag Editing] → [Classification] → [Conversion] → [Assembly] → Output
                    ↓              ↓               ↓              ↓              ↓             ↓
               Debug Log      Debug Log       Debug Log      Debug Log      Debug Log     Debug Log
```

### Key Components

1. **Pipeline Engine** (`src/pipeline/engine.py`)
   - Orchestrates stage execution
   - Handles checkpoints and resumption
   - Manages error recovery

2. **Pipeline Stages** (`src/stages/`)
   - Modular processing units
   - Independent and testable
   - Clear input/output contracts

3. **Debug Logger** (`src/utils/debug_logger.py`)
   - Detailed logging per stage
   - Structured JSON output
   - Correlation ID tracking

4. **Configuration** (`src/config.py`)
   - Feature flags for gradual rollout
   - Stage-specific settings
   - Environment variable support

## New Features

### 1. Switchable Tag Extraction Modes

```python
# Content-based extraction (default)
DST_TAG_EXTRACTION_MODE=content

# Filename-based extraction
DST_TAG_EXTRACTION_MODE=filename
```

**Content Mode**: Scans document content for tags like "Unit Tag: AHU-10"
**Filename Mode**: Extracts tags from filenames like "10_Item Summary.docx" → AHU-10

### 2. Tag Editing Capability

After tags are extracted, you can manually correct them:

**Interactive Mode**:
```bash
DST_TAG_EDIT_MODE=interactive
# Prompts you to review and edit each tag
```

**File Mode**:
```bash
DST_TAG_EDIT_MODE=file
# Creates tag_editing.json for bulk editing
```

**API Mode** (future):
```bash
DST_TAG_EDIT_MODE=api
# Integration with web interface
```

### 3. Enhanced Debugging

Every pipeline run creates detailed logs:

```
debug_logs/2024-08-01_14-30-00_a1b2c3/
├── pipeline.log          # Overall pipeline flow
├── tag_extraction.log    # Tag extraction details  
├── tag_extraction.json   # Structured data
└── stages/
    ├── tag_extraction.log
    └── tag_editing.log
```

Each log includes:
- Correlation ID for tracking requests
- Detailed processing steps
- Error context and suggestions
- Performance metrics

### 4. Checkpoint & Resume

Failed pipelines can be resumed:

```python
# Pipeline automatically saves checkpoints
# Resume from last successful stage
pipeline.run(context, resume_from='tag_extraction')
```

## Adding New Features

### 1. Create a New Stage

Use the template in `src/stages/_TEMPLATE_stage.py`:

```python
class MyNewStage(PipelineStage):
    def __init__(self, config):
        super().__init__("my_new_stage", config)
        
    def validate_input(self, context):
        # Check required input
        return True
        
    def process(self, context):
        # Do the work
        return StageResult(success=True, data={})
        
    def validate_output(self, result):
        # Verify output is correct
        return True
```

### 2. Add to Pipeline Configuration

```python
# In your pipeline setup
stages = [
    TagExtractionStage(config),
    MyNewStage(config),        # Your new stage
    TagEditingStage(config)
]
```

### 3. Add Configuration

```python
# In config.py
self.my_new_feature_enabled = self._get_env_bool(
    'DST_MY_NEW_FEATURE_ENABLED', 
    False
)
```

### 4. Write Tests

```python
# In tests/test_my_new_stage.py
class TestMyNewStage(unittest.TestCase):
    def test_basic_functionality(self):
        stage = MyNewStage({})
        context = PipelineContext({'input': 'test'})
        result = stage.run(context)
        self.assertTrue(result.success)
```

## Configuration Reference

### Pipeline Settings

```bash
# Enable/disable pipeline mode
DST_USE_PIPELINE_MODE=false        # Default: false (backward compatibility)

# Checkpoint settings
DST_SAVE_CHECKPOINTS=true          # Save state after each stage
DST_CONTINUE_ON_FAILURE=false      # Stop on first failure

# Debug settings
DST_DEBUG_MODE=false               # Enable debug breakpoints
DST_LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
```

### Tag Extraction Settings

```bash
# Extraction mode
DST_TAG_EXTRACTION_MODE=content    # 'content' or 'filename'

# Confidence settings
DST_TAG_CONFIDENCE_THRESHOLD=0.8   # Minimum confidence to accept tag
DST_TAG_FILENAME_FALLBACK=true     # Use filename if content fails
```

### Tag Editing Settings

```bash
# Enable tag editing
DST_ENABLE_TAG_EDITING=false       # Enable manual tag correction

# Editing mode
DST_TAG_EDIT_MODE=interactive      # 'interactive', 'file', or 'api'

# Auto-approval
DST_TAG_AUTO_APPROVE=true          # Auto-approve high confidence tags
```

## Migration Guide

### From Old to New System

1. **Test First**: Run `python test_pipeline.py` to verify everything works

2. **Enable Gradually**: Start with `DST_USE_PIPELINE_MODE=false` and test features

3. **Enable Pipeline**: Set `DST_USE_PIPELINE_MODE=true` when ready

4. **Monitor Logs**: Check debug logs for any issues

### Backward Compatibility

- Old JSON mapping files still work
- CLI interface unchanged
- Web interface unchanged
- Environment variables are additive

## Troubleshooting

### Common Issues

**Pipeline fails to start**:
- Check that all required files exist in `src/`
- Verify Python path includes `src/` directory
- Enable debug logging: `DST_DEBUG_MODE=true`

**Stage failures**:
- Check stage-specific log files in `debug_logs/`
- Look for correlation ID in logs to track requests 
- Verify input data format matches stage expectations

**Tag extraction issues**:
- Try switching modes: `DST_TAG_EXTRACTION_MODE=filename`
- Lower confidence threshold: `DST_TAG_CONFIDENCE_THRESHOLD=0.5`
- Enable fallback: `DST_TAG_FILENAME_FALLBACK=true`

### Debug Commands

```bash
# Test individual stages
python -c "from test_pipeline import test_stage_individually; test_stage_individually()"

# Run with maximum debugging
DST_DEBUG_MODE=true DST_LOG_LEVEL=DEBUG python dst_submittals.py documents/

# Check pipeline stages
python -c "from src.pipeline.engine import Pipeline; print('Pipeline loaded successfully')"
```

## Performance

The pipeline architecture adds minimal overhead:

- Stage execution: ~1-5ms per stage
- Logging: ~10-50MB per run (depends on verbosity)
- Checkpoints: ~1-10MB per checkpoint
- Memory: Similar to original implementation

Benefits:
- Easier debugging saves hours of troubleshooting time
- Resumable pipelines prevent re-processing on failures
- Modular stages enable independent testing and optimization

## Future Enhancements

- **Parallel Stage Execution**: Run independent stages concurrently
- **Web-based Tag Editing**: Visual interface for tag correction
- **Machine Learning**: Improve tag extraction accuracy
- **Custom Stages**: Plugin system for user-defined stages
- **Performance Monitoring**: Metrics and alerting
- **Stage Marketplace**: Share common stages between users

## Contributing

1. Follow the design philosophy in `DESIGN_PHILOSOPHY.md`
2. Use the stage template in `src/stages/_TEMPLATE_stage.py`
3. Write unit tests for new stages
4. Update this documentation for new features
5. Test both old and new modes for compatibility