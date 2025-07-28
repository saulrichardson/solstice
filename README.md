# Solstice

A clinical document processing pipeline with advanced layout detection and fact-checking capabilities.

## Getting Started

### Prerequisites

- **Python 3.11 or 3.12** (required for Detectron2 compatibility)
  - Python 3.13+ is not yet supported by Detectron2
  - We recommend using [pyenv](https://github.com/pyenv/pyenv) or [conda](https://docs.conda.io/) to manage Python versions
- **Poppler** (for PDF processing)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd solstice
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install base package**
   ```bash
   make install
   ```
   This installs the core fact-checking functionality with constraints to ensure compatibility.

4. **Install layout detection components** (optional but recommended)
   ```bash
   make install-detectron2
   ```
   This installs:
   - PyTorch and torchvision
   - Detectron2 for deep learning-based layout analysis
   - A patched version of iopath to fix model download issues
   - LayoutParser for document structure detection

   **Note:** This step can take 5-10 minutes as it builds Detectron2 from source.

### Quick Start

Process clinical PDFs with layout detection:

```bash
python -m src.cli ingest
```

This will:
- Process all PDFs in `data/clinical_files/`
- Extract text, tables, and document structure
- Save results to `data/cache/`

### Docker Setup (Alternative)

For running the gateway service in a containerized environment:

```bash
# Check Docker is installed and running
make check

# Start the gateway service
make up

# View logs
make logs

# Test the service
make test-gateway

# Stop services
make down
```

The gateway runs on http://localhost:8000 and provides API access to the processing capabilities.

## Architecture

- **Ingestion Pipeline**: Processes PDFs using layout detection to extract structured content
- **Fact Checking**: Verifies claims against a corpus of clinical documents
- **Gateway Service**: Provides API access to the processing capabilities

## Troubleshooting

### Version Conflict Warning

You may see this warning:
```
detectron2 0.6 requires iopath<0.1.10,>=0.1.7, but you have iopath 0.1.11
```

**This is expected and safe to ignore.** We intentionally use iopath 0.1.11 because it includes a critical fix for model downloads. The versions are API-compatible.

### Layout Detection Issues

If you encounter errors like "Config file does not exist" or issues with model downloads:

1. Clear the iopath cache:
   ```bash
   rm -rf ~/.torch/iopath_cache/
   ```

2. Reinstall detectron2:
   ```bash
   make install-detectron2
   ```

### Python Version Errors

If you see "Python 3.11 or 3.12 required":

1. Check your Python version:
   ```bash
   python --version
   ```

2. Install Python 3.11 using pyenv:
   ```bash
   pyenv install 3.11.9
   pyenv local 3.11.9
   ```

3. Recreate your virtual environment with Python 3.11

### Memory Issues

Layout detection is memory-intensive. If processing fails on large PDFs:
- Process PDFs individually rather than in batch
- Reduce DPI in the ingestion settings
- Ensure at least 8GB RAM is available

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
make format  # Runs black and ruff
make lint    # Checks code style
```

### Project Structure
```
solstice/
├── data/
│   ├── clinical_files/   # Input PDFs
│   └── cache/           # Processed outputs
├── src/
│   ├── cli/             # Command-line interface
│   ├── fact_check/      # Fact-checking pipeline
│   ├── gateway/         # API service
│   └── injestion/       # PDF processing pipeline
├── docker-compose.yml   # Container orchestration
├── Makefile            # Build automation
└── pyproject.toml      # Package configuration
```