#!/bin/bash
# Robust detectron2 installation script that handles all edge cases

set -e  # Exit on error

echo "=== Detectron2 Installation Script ==="

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -ne 3 ] || [ "$MINOR" -lt 11 ] || [ "$MINOR" -gt 12 ]; then
    echo "❌ Error: Python 3.11 or 3.12 required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python version $PYTHON_VERSION is compatible"

# Ensure pip and build tools are up to date
echo "Updating pip and build tools..."
pip install --upgrade pip wheel setuptools

# Clear caches
echo "Clearing caches..."
rm -rf ~/.torch/iopath_cache/

# Step 1: Install torch first (required for detectron2 build)
echo "Step 1/5: Installing PyTorch..."
pip install "torch>=2.7.0" "torchvision>=0.22.0" -c requirements-constraints.txt

# Step 2: Install detectron2 from source
echo "Step 2/5: Building detectron2 from source..."
pip install 'git+https://github.com/facebookresearch/detectron2.git' --no-build-isolation

# Step 3: Install other dependencies
echo "Step 3/5: Installing other dependencies..."
pip install "pdf2image>=1.17.0" "layoutparser[layoutmodels]>=0.3.4" -c requirements-constraints.txt

# Step 4: Force install patched iopath (must be last to override detectron2's version)
echo "Step 4/5: Installing patched iopath..."
# First install iopath dependencies
pip install aiofiles
# Then install patched iopath without deps to avoid version conflicts
pip install 'git+https://github.com/facebookresearch/iopath@e348b6797c40c9eb4c96bf75e9aaf1b248297548' --force-reinstall --no-deps

# Verify installation
echo ""
echo "Verifying installation..."
python -c "import torch; print(f'✓ PyTorch {torch.__version__}')"
python -c "import detectron2; print(f'✓ Detectron2 {detectron2.__version__}')"
python -c "import layoutparser as lp; print(f'✓ LayoutParser {lp.__version__}')"
python -c "import layoutparser as lp; assert lp.is_detectron2_available(), 'Detectron2 not available'; print('✓ Detectron2 integration working')"

echo ""
echo "✅ Detectron2 installation completed successfully!"
echo ""
echo "Note: You may see a warning about iopath version mismatch - this is expected and safe to ignore."