#!/bin/bash
# Example: Extract supporting evidence for Flublok claims

# Set gateway URL
export SOLSTICE_GATEWAY_URL=http://localhost:8000

# Extract evidence from multiple documents
python -m src.cli extract-evidence \
    data/claims/Flublok_Claims.json \
    "FlublokPI" \
    "Arunachalam et al. (2021)" \
    "Liu et al. (2024)" \
    --model gpt-4.1 \
    --output results/flublok_evidence.json

# Or use the fact_check module directly
# python -m src.fact_check FlublokPI --claims-file Flublok_Claims.json