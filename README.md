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

### Step 2: Installation

#### 2.1 Clone the repository

First, get the code:

```bash
git clone <repository-url>
cd solstice
```

The `.python-version` file will automatically activate Python 3.11.9 if you have pyenv installed.

#### 2.2 Create a virtual environment

Always use a virtual environment to avoid conflicts:

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate     # On Windows
```

You should see `(.venv)` in your terminal prompt when activated.

#### 2.3 Install the base package

Install core dependencies:

```bash
make install
```

This command:
- Checks you're using Python 3.11 or 3.12
- Installs all required packages
- Sets up the package in development mode

If you see any errors, run `make verify` to diagnose.

#### 2.4 (Optional) Install layout detection

For processing complex PDFs with tables and figures:

```bash
make install-detectron2
```

**What this installs:**
- PyTorch and torchvision for deep learning
- Detectron2 for state-of-the-art object detection
- LayoutParser for document structure analysis
- Patched dependencies for compatibility

**Notes:**
- This takes 5-10 minutes (builds from source)
- Requires ~2GB of disk space
- Downloads AI models on first use
- Skip this if you only need basic text extraction


### Step 3: Verify Installation

Check that everything is working:

```bash
make verify
```

You should see:
```
✓ fact_check package installed
✓ gateway package installed
✓ OpenAI library installed
✓ LayoutParser installed (or skip message if not installed)
✓ Poppler installed
```

### Step 4: Configuration

#### 4.1 API Keys

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-...
```

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
# Run all fact-checking agents
python -m src.cli run-study

# Run specific agents only
python -m src.cli run-study --agents supporting_evidence regex_verifier
```

Available agents:
- `supporting_evidence` - Finds evidence supporting claims
- `regex_verifier` - Pattern-based verification
- `clinical_trial_extractor` - Extracts trial data

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

- **Ingestion Pipeline**: Processes PDFs using layout detection to extract structured content
  - Uses native PDF text extraction (PyMuPDF) with automatic text processing
  - Applies intelligent spacing fixes using WordNinja
  - Automatically handles tables and figures as images
  - Modular text processing service for consistent text quality
- **Fact Checking**: Agent-based system that extracts supporting evidence for claims from clinical documents
- **Gateway Service**: Proxy service for LLM API calls (OpenAI, Anthropic, etc.)

### Text Processing

The ingestion pipeline includes an automatic text processing service that:
- Fixes spacing issues common in PDFs (e.g., "theinformationneeded" → "the information needed")
- Preserves medical terms and trademarks (e.g., "Flublok®")
- Handles punctuation and unit normalization
- Uses WordNinja for intelligent word segmentation based on Google n-grams

This ensures that downstream components (fact-checking, LLMs) receive properly formatted text.

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
│   └── injestion/       # PDF processing pipeline
│       ├── processing/  # Text cleaning & correction
│       ├── storage/     # Data persistence
│       └── marketing/   # Document analysis
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