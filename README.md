solstice assignment

## Requirements

- Python 3.11.x (required for Detectron2)
- Poppler (for PDF processing)

## Quick Start

```bash
# Clone the repo
git clone <repo-url>
cd solstice

# Ensure Python 3.11 is active (the .python-version file will auto-select if using pyenv)
python --version  # Should show Python 3.11.x

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install base package
make install

# (Optional) Install Detectron2 for layout detection
make install-detectron2
```

## System Dependencies

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

See `LAYOUT_PARSER_SETUP.md` for detailed setup instructions.
