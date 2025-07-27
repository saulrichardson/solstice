#!/bin/bash
# This script ensures the project uses its own .env file for API keys
# rather than shell environment variables

# Unset any shell-defined OPENAI_API_KEY
unset OPENAI_API_KEY

echo "✓ Shell OPENAI_API_KEY unset"
echo "✓ Project will now use API key from .env file"

# Optionally activate a virtual environment if you have one
# source venv/bin/activate

# Run the command passed as arguments
if [ $# -gt 0 ]; then
    exec "$@"
fi