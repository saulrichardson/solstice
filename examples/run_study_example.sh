#!/bin/bash
# Example: Run fact-checking study with new architecture

# Set gateway URL
export SOLSTICE_GATEWAY_URL=http://localhost:8000

echo "Running fact-checking study with agent pipeline..."
echo ""

# Run with all defaults (Flublok claims, all documents)
python -m src.cli run-study

# Or run with specific documents
# python -m src.cli run-study --documents FlublokPI "Liu et al. (2024)"

# Or run with custom model
# python -m src.cli run-study --model o4-mini

# Or save to specific output file
# python -m src.cli run-study --output results/my_study.json