#!/bin/bash
# Setup script - Docker is required

set -e

echo "Fact Check Gateway Setup"
echo "======================="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    echo ""
    echo "Please install Docker from:"
    echo "https://docs.docker.com/get-docker/"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running"
    echo ""
    echo "Please start Docker and run this script again."
    exit 1
fi

echo "✓ Docker is installed and running"
echo ""

# Create .env if needed
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file"
fi

# Check for API key
if grep -q "sk-\.\.\." .env 2>/dev/null || ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "⚠️  Please add your OpenAI API key to the .env file:"
    echo ""
    echo "   OPENAI_API_KEY=sk-your-key-here"
    echo ""
    echo "Get your key from: https://platform.openai.com/api-keys"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Start services
echo ""
echo "Starting services..."
docker compose up -d

echo ""
echo "✅ Setup complete!"
echo ""
echo "Gateway is running at: http://localhost:4000"
echo ""
echo "Test with:"
echo "  curl http://localhost:4000/health"
echo ""
echo "View logs:"
echo "  make logs"