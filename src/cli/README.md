# CLI Module

Command-line interface for Solstice operations.

## Commands

### `ingest`
Process clinical PDFs into structured documents.
```bash
python -m src.cli ingest
```
- Input: `data/clinical_files/`
- Output: `data/scientific_cache/`

### `ingest-marketing`
Process marketing PDFs with specialized layout handling.
```bash
python -m src.cli ingest-marketing
```
- Input: `data/marketing_slide/`
- Output: `data/marketing_cache/`

### `run-study`
Run fact-checking across claims and documents.
```bash
python -m src.cli run-study
```
- Uses cached documents
- Outputs to `data/studies/`

### `clear-all-cache`
Remove all cached data.
```bash
python -m src.cli clear-all-cache
```