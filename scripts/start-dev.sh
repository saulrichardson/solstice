#!/bin/bash
set -e

echo "🚀 Starting fact-check development environment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please update .env with your API keys!"
    exit 1
fi

# Start services
docker-compose up -d

echo "✅ Gateway running at http://localhost:4000"
echo "📊 Gateway docs at http://localhost:4000/docs"
echo ""
echo "Test with: curl http://localhost:4000/health"
echo ""
echo "Stop with: docker-compose down"