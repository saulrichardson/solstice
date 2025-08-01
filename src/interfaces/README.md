# Interfaces Module

Shared data structures used throughout Solstice.

## Overview

This module defines the common data types that different parts of Solstice use to communicate. Think of it as the "language" that allows components to understand each other.

## Main Components

### Document Structure
The `Document` class represents a processed PDF:
- Contains a list of content blocks (text, figures, tables)
- Tracks reading order for each page
- Stores metadata about the source file

### Block Types
Each piece of content is a `Block`:
- **Text blocks**: Paragraphs, titles, lists
- **Figure blocks**: Images, charts, diagrams
- **Table blocks**: Structured data

### Content Types
Enumerations that classify content:
- What type of content (text, figure, table)
- How to format output (plain text, with placeholders, etc.)
- Block roles (title, paragraph, caption, etc.)

## How It's Used

1. **Ingestion creates Documents**: When PDFs are processed, they become Document objects
2. **Fact-checking reads Documents**: Agents search through blocks to find evidence
3. **Results reference Documents**: Evidence points back to specific blocks

## Example

```python
# A processed document looks like this
document = Document(
    blocks=[
        Block(id="1", text="This is a title", role="Title", page=0),
        Block(id="2", text="This is a paragraph", role="Text", page=0),
        Block(id="3", image_path="figure1.png", role="Figure", page=0)
    ],
    reading_order=[[1, 2, 3]],  # Order for page 0
    metadata={"source": "example.pdf"}
)
```

This structure allows all Solstice components to work with documents in a consistent way.