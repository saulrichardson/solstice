#!/bin/bash
set -e

echo "🚀 Setting up Solstice..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -ne 3 ] || [ "$MINOR" -lt 11 ] || [ "$MINOR" -gt 12 ]; then
    echo "❌ Python 3.11 or 3.12 required (found $PYTHON_VERSION)"
    echo ""
    echo "Quick fix options:"
    echo "1. Using pyenv (recommended):"
    echo "   brew install pyenv  # or see https://github.com/pyenv/pyenv"
    echo "   pyenv install 3.11.9"
    echo "   pyenv local 3.11.9"
    echo ""
    echo "2. Using conda:"
    echo "   conda create -n solstice python=3.11"
    echo "   conda activate solstice"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION"

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
    echo ""
    echo "Please activate it and run this script again:"
    echo "  source .venv/bin/activate"
    echo "  ./setup.sh"
    exit 0
fi

echo "✓ Virtual environment active"

# Check system dependencies
if ! command -v pdfinfo >/dev/null 2>&1; then
    echo "⚠️  Poppler not installed (required for PDF processing)"
    echo "  macOS: brew install poppler"
    echo "  Linux: sudo apt-get install poppler-utils"
    echo ""
fi

# Install base package
echo "Installing base package..."
pip install --upgrade pip
pip install -c requirements-constraints.txt -e .
echo "✓ Base package installed"

# Optional: Install Detectron2
echo ""
read -p "Install Detectron2 for layout detection? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Detectron2 (this may take 5-10 minutes)..."
    pip install -c requirements-constraints.txt -r requirements-detectron2.txt
    echo "✓ Detectron2 installed"
fi

# Verify installation
echo ""
echo "Verifying installation..."
python -c "import fact_check; print('✓ fact_check ready')"
python -c "import gateway; print('✓ gateway ready')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and add your OpenAI API key"
echo "2. Run 'make up' to start services"
echo "3. Run 'make verify' to check all dependencies"