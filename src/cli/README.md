# Solstice CLI

Centralized command-line interface for the Solstice document processing and fact-checking system.

## Architecture

The CLI module provides a unified entry point for all Solstice operations. It follows a subcommand pattern using Python's argparse, with each command implemented in its own module.

### Key Components

- **`__main__.py`**: Main dispatcher that routes commands to their implementations
- **`ingest.py`**: Processes clinical PDFs using the scientific ingestion pipeline
- **`ingest_marketing.py`**: Processes marketing PDFs with specialized layout detection
- **`run_study.py`**: Executes fact-checking studies across claims and documents
- **`clean.py`**: Cache management utilities

## Available Commands

### 1. PDF Ingestion (`ingest`)

Process clinical PDFs with optimized settings:

```bash
# Process all PDFs in data/clinical_files/
python -m src.cli ingest

# Use custom output directory
python -m src.cli ingest --output-dir /path/to/output
```

**Default behavior:**
- Input: `data/clinical_files/*.pdf`
- Output: `data/scientific_cache/`
- Pipeline: Scientific document pipeline (400 DPI, clinical document optimizations)

### 2. Marketing PDF Ingestion (`ingest-marketing`)

Process marketing materials with specialized layout detection:

```bash
# Process all PDFs in data/marketing_slide/
python -m src.cli ingest-marketing

# Process a specific marketing PDF
python -m src.cli ingest-marketing /path/to/marketing.pdf

# Use custom output directory
python -m src.cli ingest-marketing --output-dir /custom/output
```

**Default behavior:**
- Input: `data/marketing_slide/*.pdf` (when no file specified)
- Output: `data/marketing_cache/`
- Pipeline: Marketing-optimized pipeline (enhanced layout detection)

### 3. Run Fact-Checking Study (`run-study`)

Execute fact-checking analysis across claims and documents:

```bash
# Use default claims and all cached documents
python -m src.cli run-study

# Specify custom claims and documents
python -m src.cli run-study --claims claims.json --documents doc1.json doc2.json
```

### 4. Clear Cache (`clear-all-cache`)

Remove the entire cache directory (requires confirmation):

```bash
python -m src.cli clear-all-cache
```

## Architecture Details

### Command Registration Flow

1. User invokes `python -m src.cli <command>`
2. `__main__.py` parses arguments and identifies the command
3. Appropriate module is imported and its `main()` function is called
4. Each command module handles its specific logic

### Integration Points

- **Ingestion Pipeline**: Commands use `src.injestion` for document processing
- **Fact Checking**: Integrates with `src.fact_check` for claim verification
- **Storage**: Uses `src.injestion.shared.storage` for cache management
- **Configuration**: Leverages `src.core.config` for settings

## Adding New Commands

To add a new command:

1. Create a new module in `src/cli/` (e.g., `new_command.py`)
2. Implement a `main()` function that accepts command-specific arguments
3. Add the command parser to `__main__.py`:
   ```python
   new_parser = subparsers.add_parser("new-command", help="Description")
   new_parser.add_argument("--option", help="Option description")
   ```
4. Add the routing logic in the main dispatcher

## Error Handling

The CLI provides user-friendly error messages for common issues:
- Missing input directories
- No files to process
- Invalid arguments
- Processing failures

All errors are reported via stdout with appropriate exit codes.