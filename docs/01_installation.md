# Installation Guide

This guide will walk you through setting up Solstice step by step. The setup has two parts:
1. **Basic setup** (required) - Core functionality for text extraction and fact-checking
2. **Advanced setup** (optional) - Adds AI-powered layout detection for complex PDFs

## Prerequisites

### Python Version (Critical)

- **Python 3.11 or 3.12** (required for Detectron2 compatibility)
  - Python 3.13+ is not yet supported by Detectron2
  - We recommend using [pyenv](https://github.com/pyenv/pyenv) or [conda](https://docs.conda.io/) to manage Python versions
  
  **Automatic version management with pyenv:**
  ```bash
  # Install pyenv (if not already installed)
  # macOS: brew install pyenv
  # Linux: curl https://pyenv.run | bash
  
  # Install Python 3.11.9 (exact version used by this project)
  pyenv install 3.11.9
  
  # The project includes a .python-version file that will automatically
  # activate Python 3.11.9 when you enter the directory
  cd solstice
  python --version  # Should show Python 3.11.9
  ```

### System Dependencies

- **Poppler** (for PDF processing)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

## Complete Installation Example

Here's the exact workflow to get everything installed from scratch:

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd solstice
```

### Step 2: Set up Python 3.11 (CRITICAL)

**Option A: If you have pyenv installed:**
```bash
# The project includes a .python-version file that specifies 3.11.9
# Pyenv will automatically use it when you enter the directory
cd solstice
python --version  # Should show Python 3.11.x
```

**Option B: If you DON'T have pyenv:**
```bash
# Check your Python version
python3 --version

# If it's not 3.11.x or 3.12.x, you need to install Python 3.11:
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11 python3.11-venv
# Then use python3.11 explicitly in the next steps
```

### Step 3: Create and Activate Virtual Environment

```bash
# IMPORTANT: If your default python3 is NOT 3.11, use python3.11 explicitly:
python3.11 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux
# On Windows: .venv\Scripts\activate

# Verify you're using the right Python version
python --version  # Must show Python 3.11.x or 3.12.x
```

**Common issue:** If you see Python 3.13.x, you created the venv with the wrong Python version. Delete it and recreate:
```bash
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install the Base Package

```bash
# Upgrade pip first (important!)
pip install --upgrade pip

# Install the base package
make install
```

This will:
- Verify Python version is 3.11 or 3.12
- Install all core dependencies
- Set up the package in development mode

### Step 5: (Optional) Install Detectron2 for Layout Detection

For processing complex PDFs with tables and figures:

```bash
make install-detectron2
```

**What this does:**
- Installs PyTorch and detectron2 for layout detection
- Builds detectron2 from source (required for Python 3.11+)
- Installs a patched version of iopath to fix model download issues
- Takes 5-10 minutes and requires ~2GB disk space

If the make command fails, you can install manually:

```bash
# Clear iopath cache
rm -rf ~/.torch/iopath_cache/

# Install dependencies
pip install torch torchvision
pip install 'git+https://github.com/facebookresearch/detectron2.git' --no-build-isolation
pip install 'git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548' --force-reinstall
pip install layoutparser[layoutmodels]
```

**Note:** You'll see a version warning about iopath - this is expected and safe to ignore.

### Step 6: Verify Installation

```bash
make verify
```

Expected output:
```
✓ fact_check package installed
✓ gateway package installed  
✓ OpenAI library installed
✓ LayoutParser installed
✓ Poppler installed

Python: Python 3.11.13
Pip:    pip 25.1.1 from /path/to/.venv/lib/python3.11/site-packages/pip (python 3.11)
```

## Configuration

### Environment File Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-api-key-here
```

Note: The gateway service requires this for API calls. Leave other settings at defaults.

### Data Directories

The project expects this structure:
```
data/
├── clinical_files/   # Put your input PDFs here
└── cache/           # Processed outputs go here
```

Create them if needed:
```bash
mkdir -p data/clinical_files data/cache
```

## Quick Start Guide

Now you're ready to use Solstice! Here are the main workflows:

### Process PDFs

Place your PDFs in `data/clinical_files/`, then:

```bash
python -m src.cli ingest
```

This will:
- Process all PDFs in the input directory
- Extract text with intelligent spacing correction
- Detect and extract tables/figures (if Detectron2 installed)
- Save structured JSON to `data/cache/`

### Run Fact Checking

After ingesting documents, extract evidence for claims:

```bash
# Run fact-checking pipeline
python -m src.cli run-study
```

This runs the complete fact-checking pipeline that:
- Searches for evidence supporting each claim
- Verifies and validates found evidence
- Checks completeness of evidence
- Analyzes images for supporting evidence
- Presents results in structured format

By default, it uses claims from `data/claims/Flublok_Claims.json` and searches all processed documents.

**Note**: The marketing folder contains a specialized parser specifically designed for Flublok marketing PDFs, using PrimaLayout for better detection of marketing material layouts.

### Using the Gateway Service

Start the API gateway for production use:

```bash
# Start services (auto-handles Docker issues)
make up

# Check logs
make logs

# Stop when done
make down
```

The gateway runs at `http://localhost:8000` and provides:
- OpenAI-compatible API endpoints
- Request/response logging
- Automatic retries and error handling

## Docker Setup (Production)

For production deployment using Docker:

```bash
# Check your Docker setup
make docker-status

# Start all services
docker compose up -d

# Scale gateway instances
docker compose up -d --scale gateway=3
```

**Colima users**: The Makefile automatically restarts Colima if Docker is unresponsive.

## Troubleshooting

### Python Version Issues (Most Common Problem)

**Problem:** `make install` fails with "Python 3.11 or 3.12 required (found 3.13.x)"

**Solution:** Your virtual environment was created with the wrong Python version.

```bash
# 1. Deactivate and remove the incorrect venv
deactivate
rm -rf .venv

# 2. Install Python 3.11 if needed
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11 python3.11-venv

# 3. Create venv with correct Python
python3.11 -m venv .venv
source .venv/bin/activate

# 4. Verify
python --version  # Must show 3.11.x or 3.12.x

# 5. Continue installation
pip install --upgrade pip
make install
```

**Problem:** "command not found: python" when creating venv

**Solution:** Use `python3` or `python3.11` explicitly:
```bash
python3.11 -m venv .venv
```

### Version Conflict Warning

You may see this warning:
```
detectron2 0.6 requires iopath<0.1.10,>=0.1.7, but you have iopath 0.1.11
```

**This is expected and safe to ignore.** We intentionally use a patched iopath that fixes model download issues while remaining API-compatible.

### Detectron2 Issues

If you encounter errors like "Config file does not exist" or model download failures:

1. Clear the iopath cache: `rm -rf ~/.torch/iopath_cache/`
2. Ensure the patched iopath is installed
3. Check your internet connection

The version warning about iopath is expected:
```
detectron2 0.6 requires iopath<0.1.10,>=0.1.7, but you have iopath 0.1.11
```
This is safe to ignore - the patched version is API-compatible.

### Memory Issues

Layout detection is memory-intensive. If processing fails on large PDFs:
- Process PDFs individually rather than in batch
- Reduce DPI in the ingestion settings
- Ensure at least 8GB RAM is available

### Docker Issues

**Problem:** Docker daemon not running

**Solution:** The Makefile includes automatic Docker/Colima restart:
```bash
make up  # Automatically restarts Docker if needed
```

**Problem:** Port already in use

**Solution:** Check what's using port 8000:
```bash
lsof -i :8000
# Kill the process or change the port in docker-compose.yml
```

## Complete Installation Script

For reference, here's a complete installation script:

```bash
#!/bin/bash
# Complete Solstice installation script

# 1. Clone and enter the project
git clone <repository-url>
cd solstice

# 2. Check Python version
python3 --version
# If not 3.11.x, install it (e.g. on macOS: brew install python@3.11)

# 3. Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# 4. Verify the version inside the venv
python --version  # Must show Python 3.11.x

# 5. Upgrade build tools (mitigates most build errors)
pip install --upgrade pip wheel setuptools

# 6. Install core dependencies
make install

# 7. (Optional) Install Detectron2 for layout detection
make install-detectron2

# 8. Verify everything is in place
make verify

# 9. Provide your OpenAI key
cp .env.example .env && echo "OPENAI_API_KEY=sk-…" >> .env

# 10. Test the CLI
python -m src.cli --help

# 11. Create data directories
mkdir -p data/clinical_files data/cache

echo "Installation complete! Place PDFs in data/clinical_files/ and run 'make ingest'"
```


## Next Steps

After installation:
1. Place your PDFs in `data/clinical_files/`
2. Run `make ingest` to process them
3. Run `make run-study` to fact-check claims
4. Check results in `data/cache/` and `data/studies/`

For more details on the system architecture and components, see the [Project Overview](00_project_overview.md).

