# Interfaces Module

Common data structures for document representation.

## Main Types

### Document
Represents a processed PDF with:
- `blocks` - List of content (text, figures, tables)
- `reading_order` - Block order per page
- `metadata` - Source file info

### Block
Individual content unit with:
- `text` - For text blocks
- `image_path` - For figures/tables
- `role` - Type (Text, Title, Figure, Table)
- `bbox` - Location on page

## Usage

```python
# Documents flow through the system
PDF → Ingestion → Document → Fact-checking → Evidence
```

All components use these structures to ensure consistency.