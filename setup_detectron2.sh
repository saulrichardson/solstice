#!/bin/bash
set -e

echo "Setting up Detectron2 for layout parser..."

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -lt 11 ] || [ "$PYTHON_MINOR" -gt 12 ]; then
    echo "Error: Python 3.11 or 3.12 required (found $PYTHON_VERSION)"
    echo "Please use pyenv or conda to install Python 3.11"
    exit 1
fi

# Check if poppler is installed
if ! command -v pdfinfo &> /dev/null; then
    echo "Warning: Poppler not installed. PDF processing will fail."
    echo "Install with:"
    echo "  macOS: brew install poppler"
    echo "  Linux: sudo apt-get install poppler-utils"
fi

# Clear any existing cache
echo "Clearing iopath cache..."
rm -rf ~/.torch/iopath_cache/

# Install PyTorch first (required for Detectron2 build)
echo "Installing PyTorch..."
pip install torch torchvision

# Install Detectron2
echo "Installing Detectron2..."
pip install git+https://github.com/facebookresearch/detectron2.git

# Install patched iopath (MUST be after Detectron2)
echo "Installing patched iopath..."
pip install --force-reinstall git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548

# Verify installation
echo "Verifying installation..."
python -c "import layoutparser as lp; assert lp.is_detectron2_available(), 'Detectron2 not available'"

echo "Setup complete! You can now run: python test_layout_parser.py"