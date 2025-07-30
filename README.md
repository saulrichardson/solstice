# Solstice

A clinical document processing pipeline with advanced layout detection and fact-checking capabilities.

## Overview

Solstice is a comprehensive system for processing clinical documents (PDFs, clinical trial data, FDA documents) with three main components:

1. **Document Ingestion** - Extracts text, tables, and figures from PDFs using state-of-the-art layout detection
2. **Fact Checking** - AI-powered agents that verify claims and extract supporting evidence from documents
3. **Gateway Service** - API proxy for LLM interactions with monitoring and caching

### Key Features

- **Advanced PDF Processing**: Uses Detectron2-based layout detection to accurately extract complex document structures
- **Intelligent Text Correction**: Automatically fixes common PDF text extraction issues (spacing, punctuation)
- **Multi-Agent System**: Modular fact-checking agents for different verification tasks
- **Production Ready**: Docker-based deployment with health checks and monitoring
- **Extensible**: Easy to add new document types, agents, or processing steps

### Use Cases

- Processing clinical trial protocols and results
- Extracting data from FDA submissions and approvals
- Verifying claims in medical literature
- Building structured datasets from unstructured clinical documents

## Getting Started

This guide will walk you through setting up Solstice step by step. The setup has two parts:
1. **Basic setup** (required) - Core functionality for text extraction and fact-checking
2. **Advanced setup** (optional) - Adds AI-powered layout detection for complex PDFs

### Step 1: Check Prerequisites

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
- **Poppler** (for PDF processing)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

### Step 2: Installation - Complete Example

Here's the exact workflow to get everything installed from scratch:

#### 2.1 Clone the repository

```bash
git clone <repository-url>
cd solstice
```

#### 2.2 Set up Python 3.11 (CRITICAL - detectron2 requires 3.11 or 3.12)

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

#### 2.3 Create and activate virtual environment

```bash
# IMPORTANT: If your default python3 is NOT 3.11, use python3.11 explicitly:
python3.11 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On macOS/Linux

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

#### 2.4 Install the base package

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

#### 2.5 (Optional but recommended) Install detectron2 for layout detection

For processing complex PDFs with tables and figures:

```bash
make install-detectron2
```

**What this installs:**
- PyTorch and torchvision for deep learning
- Detectron2 for state-of-the-art object detection (built from source)
- LayoutParser for document structure analysis
- **Patched iopath** to fix model download issues (installed after detectron2)

**Note about the installation:**
- Detectron2 is built from source since pre-built wheels aren't available for Python 3.11+
- The installation uses `--no-build-isolation` to ensure torch is available during build
- A patched version of iopath is installed to fix the `?dl=1` query parameter issue
- The iopath cache is cleared before installation to avoid conflicts

**Notes:**
- This takes 5-10 minutes (builds from source)
- Requires ~2GB of disk space
- Downloads AI models on first use
- Skip this if you only need basic text extraction


#### 2.6 Verify everything works

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

### Complete Installation Example

Here's a real-world example of the entire installation process:

```bash
# 1. Clone and enter the project
git clone <repository-url>
cd solstice

# 2. Check Python version
python3 --version
# If not 3.11.x, install it:
# brew install python@3.11  # macOS

# 3. Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# 4. Verify Python version in venv
python --version  # Must show Python 3.11.x

# 5. Upgrade pip (CRITICAL - prevents build errors)
pip install --upgrade pip wheel setuptools

# 6. Install base package
make install  # This also upgrades pip/wheel/setuptools automatically

# 7. Install detectron2 (for advanced PDF processing)
make install-detectron2
# Note: You'll see a warning about iopath version - this is expected and safe

# 8. Verify installation
make verify

# 9. Set up environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 10. Test the CLI
python -m src.cli --help
```

### Step 3: Configuration

#### 3.1 Set up environment file

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-api-key-here
```

Note: The gateway service requires this for API calls. Leave other settings at defaults.

#### 4.2 Data Directories

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

### Step 5: Quick Start

Now you're ready to use Solstice! Here are the main workflows:

#### Process PDFs

Place your PDFs in `data/clinical_files/`, then:

```bash
python -m src.cli ingest
```

This will:
- Process all PDFs in the input directory
- Extract text with intelligent spacing correction
- Detect and extract tables/figures (if Detectron2 installed)
- Save structured JSON to `data/cache/`

#### Run Fact Checking

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

#### Using the Gateway Service

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

### Step 6: Docker Setup (Production)

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

## Architecture

### Core Components

- **Ingestion Pipeline** (`src/injestion/`): Processes PDFs to extract structured content
  - Native PDF text extraction using PyMuPDF
  - Intelligent text correction with WordNinja
  - Optional layout detection for tables/figures (requires Detectron2)
  - Special marketing module for Flublok marketing materials (uses PrimaLayout)
  - Saves extracted content as JSON in `data/cache/`

- **Fact Checking System** (`src/fact_check/`): Multi-agent pipeline for evidence extraction
  - Orchestrator coordinates multiple specialized agents
  - Each agent handles specific verification tasks
  - Results saved with full evidence trails

- **Gateway Service** (`src/gateway/`): API proxy for LLM interactions
  - OpenAI-compatible endpoints
  - Request/response caching
  - Automatic retries and error handling
  - Runs on port 8000 by default

### Text Processing

The ingestion pipeline includes an automatic text processing service that:
- Fixes spacing issues common in PDFs (e.g., "theinformationneeded" → "the information needed")
- Preserves medical terms and trademarks (e.g., "Flublok®")
- Handles punctuation and unit normalization
- Uses WordNinja for intelligent word segmentation based on Google n-grams

This ensures that downstream components (fact-checking, LLMs) receive properly formatted text.

## Troubleshooting

### Common Issues

#### Python Version Issues (Most Common Problem)

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

#### Version Conflict Warning

You may see this warning:
```
detectron2 0.6 requires iopath<0.1.10,>=0.1.7, but you have iopath 0.1.11
```

**This is expected and safe to ignore.** We intentionally use a patched iopath that fixes model download issues while remaining API-compatible.

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

### Code Quality

```bash
# Format code automatically
make format

# Check code style
make lint

# Run tests
pytest
```

### Project Structure

```
solstice/
├── data/
│   ├── clinical_files/   # Input PDFs go here
│   └── cache/           # Processed outputs stored here
├── src/
│   ├── cli/             # Command-line interface
│   ├── fact_check/      # Fact-checking agents
│   ├── gateway/         # API proxy service  
│   ├── injestion/       # PDF processing pipelines
│   │   ├── scientific/  # Main pipeline for scientific/clinical PDFs
│   │   ├── marketing/   # Specialized pipeline for Flublok marketing PDFs
│   │   └── shared/      # Common utilities
│   │       ├── processing/  # Text cleaning & correction
│   │       ├── storage/     # Data persistence
│   │       └── visualization/ # Visual output generation
│   ├── core/            # Core utilities
│   ├── interfaces/      # Shared interfaces
│   └── util/            # Helper utilities
├── docker-compose.yml   # Container orchestration
├── Makefile            # Common commands
├── pyproject.toml      # Package & dependencies
├── requirements-*.txt  # Dependency constraints
└── .python-version     # Python 3.11.9 (for pyenv)
```

### Adding New Features

1. **New Document Types**: Add parsers in `src/injestion/`
2. **New Fact-Check Agents**: Add to `src/fact_check/agents/`
3. **New API Endpoints**: Modify `src/gateway/`

### Common Commands

```bash
make help         # Show all available commands
make install      # Install base package
make verify       # Check installation
make up          # Start services
make logs        # View logs
make down        # Stop services
make format      # Format code
make lint        # Check code style
make clean       # Remove cache files
```