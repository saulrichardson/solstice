#!/bin/bash
# Example: Extract evidence using all defaults

# Set gateway URL
export SOLSTICE_GATEWAY_URL=http://localhost:8000

echo "Running evidence extraction with defaults..."
echo "Claims: data/claims/Flublok_Claims.json"
echo "Documents: All PDFs in data/clinical_files/"
echo ""

# Run with all defaults - no arguments needed!
python -m src.cli extract-evidence

# Or to see what documents are being used:
# python -m src.cli extract-evidence --help

# Or to use specific documents only:
# python -m src.cli extract-evidence --documents FlublokPI "Liu et al. (2024)"