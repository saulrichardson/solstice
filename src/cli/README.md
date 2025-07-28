# Solstice CLI

Centralized command-line interface for all Solstice packages.

## Usage

### PDF Ingestion

Process all PDFs in the default clinical files directory:

```bash
# From the project root
python -m src.cli ingest

# Or with custom output directory
python -m src.cli ingest --output-dir /path/to/output
```

**Default behavior:**
- Input: `data/clinical_files/*.pdf`
- Output: `data/cache/`
- Settings: Optimized for clinical documents (400 DPI, merge overlapping boxes, etc.)

### Adding New Commands

To add a new command:

1. Create a new module in `src/cli/` (e.g., `fact_check.py`)
2. Add the command to `__main__.py`
3. Follow the same pattern as `ingest.py`

Example structure:
```
src/cli/
├── __init__.py
├── __main__.py
├── ingest.py      # PDF processing
├── fact_check.py  # Fact checking (future)
└── gateway.py     # Gateway operations (future)
```