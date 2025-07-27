# Layout Parser Setup Guide

This guide explains how to set up the layout detection system with Detectron2.

## Prerequisites

### 1. Python Version
- **Required**: Python 3.11.x
- **Not supported**: Python 3.13+ (Detectron2 compatibility issue)

### 2. System Dependencies
Install Poppler for PDF processing:

**macOS:**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**Windows:**
Download from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)

## Installation Steps

### 1. Set up Python 3.11 environment

**Using pyenv (recommended):**
```bash
# Install Python 3.11
pyenv install 3.11.9
pyenv local 3.11.9

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Using conda:**
```bash
conda create -n solstice python=3.11
conda activate solstice
```

### 2. Install dependencies

```bash
# Install in the correct order
pip install -r requirements-detectron2.txt
```

**Important**: The installation order matters! The patched iopath must be installed AFTER detectron2.

### 3. Verify installation

```bash
python -c "import layoutparser as lp; print('Detectron2 available:', lp.is_detectron2_available())"
```

Should output: `Detectron2 available: True`

## Running the Layout Parser

```bash
python test_layout_parser.py
```

This will:
1. Process the PDF using Detectron2's PubLayNet model
2. Detect layout elements (text, titles, figures, tables, lists)
3. Save results to `layout_detection_results.json`

## Troubleshooting

### "?dl=1" file not found error
If you see errors about files ending in `?dl=1`, the patched iopath didn't install correctly:

```bash
# Clear cache
rm -rf ~/.torch/iopath_cache/

# Reinstall patched iopath
pip install --force-reinstall git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548
```

### ModuleNotFoundError: No module named 'torch'
Detectron2 build requires PyTorch during installation. Install PyTorch first:

```bash
pip install torch torchvision
pip install git+https://github.com/facebookresearch/detectron2.git
```

### Python version issues
If using Python 3.13+, you'll get build errors. Downgrade to Python 3.11:

```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

## Docker Deployment (Optional)

For consistent deployment, use the provided Dockerfile:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements-detectron2.txt .

# Install Python dependencies in correct order
RUN pip install --no-cache-dir -r requirements-detectron2.txt

# Copy application code
COPY . .

CMD ["python", "test_layout_parser.py"]
```