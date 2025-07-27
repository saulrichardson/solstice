# Fact Check - Citation Finder

A project for finding citations to back up claims from scientific publications using LLMs.

## Requirements

- Docker (required)
- OpenAI API key

## Quick Start

```bash
git clone <repo>
cd fact-check
./scripts/setup.sh
```

This will:
1. Check that Docker is installed
2. Create your .env file
3. Guide you through adding your API key
4. Start the gateway

## Architecture

The project has two parts:

1. **LLM Gateway (runs in Docker)** - A FastAPI service that:
   - Implements OpenAI's new Responses API (July 2025)
   - Supports GPT-4.1 family (1M token context) and o4-mini models
   - Enables stateful conversations with previous_response_id
   - Provides built-in tools (web_search_preview, code_interpreter, etc.)
   - Implements caching via Redis
   - Handles retry logic and logging
   - Runs on port 4000 by default (configurable via SOLSTICE_GATEWAY_PORT in .env)

2. **Your Application (runs locally)** - Your Python code that:
   - Uses the `ResponsesClient` to interact with the Responses API
   - Implements your agent logic
   - Processes documents, finds citations, etc.

```
fact-check/
├── src/
│   └── fact_check/           # Main Python package
│       ├── gateway/          # FastAPI LLM gateway
│       │   └── app/
│       │       ├── providers/    # OpenAI provider
│       │       ├── middleware/   # Logging, retry logic
│       │       └── cache.py      # Redis caching
│       ├── core/             # Shared utilities
│       │   └── responses_client.py  # Responses API client
│       └── apps/             # Applications
│           └── citation_finder/  # Your citation app
├── tests/                    # Test suite
├── docker/                   # Docker configurations
└── scripts/                  # Dev utilities
```

## Usage

### Start the gateway
```bash
make up
```

### Test the setup
```bash
# Test 1: Verify gateway is working (no Python needed)
make test-gateway

# Test 2: Verify Python client (requires virtual environment)
# First activate your virtual environment, then:
python scripts/test-client.py
```

### Use from Python

Your application code runs locally and connects to the gateway:

```bash
# Create a virtual environment for YOUR code
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the fact-check package
make install
```

Then in your Python scripts:
```python
from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

# Simple completion
response = client.complete("What is the speed of light?", model="gpt-4.1-mini")

# With built-in tools
response = client.complete_with_tools(
    "Search for recent AI breakthroughs",
    tools=["web_search_preview"],
    model="gpt-4.1"
)

# With custom tools
tools = [{
    "type": "function", 
    "function": {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"]
        }
    }
}]
response = client.complete_with_tools("What's the weather in NYC?", tools=tools)

# Streaming
for chunk in client.stream_response("Write a poem"):
    if chunk.get("output_text"):
        print(chunk["output_text"], end="")

# Reasoning models (o4-mini with encrypted reasoning)
response = client.complete_with_reasoning(
    "Solve this step by step: If a train travels...",
    model="o4-mini",
    reasoning_level="high"
)

# Stateful conversation
resp1 = client.create_stateful_conversation(
    "My name is Alice and I'm learning Python.",
    instructions="Remember user details throughout our conversation"
)
print(f"Assistant: {resp1['output_text']}")

resp2 = client.continue_conversation(
    "What programming language am I learning?",
    previous_response_id=resp1['id']
)
print(f"Assistant: {resp2['output_text']}")
```

### View logs
```bash
make logs
```

### Stop services
```bash
make down
```

## Available Models

### GPT-4.1 Family (1M token context)
- `gpt-4.1` - Most capable model with massive context
- `gpt-4.1-mini` - Balanced performance and cost
- `gpt-4.1-nano` - Fastest and most affordable

All GPT-4.1 models support:
- 1 million token context window
- Built-in and custom tools
- Parallel tool calls
- Stateful conversations
- Streaming responses

### o4-mini (Tool-driven Reasoning)
- `o4-mini` - Advanced reasoning with encrypted thought process
- 200k token context
- Specialized for complex, multi-step reasoning
- Tool-aware reasoning capabilities

### Built-in Tools
The Responses API includes these tools out of the box:
- `web_search_preview` - Search the web
- `code_interpreter` - Execute Python code
- `file_search` - Search through uploaded files
- `image_generation` - Generate images
- Custom function tools

## Development

All commands:
```bash
make help         # Show available commands
make check        # Verify Docker is installed
make up          # Start services
make down        # Stop services
make logs        # View logs
make test        # Run tests
make lint        # Check code quality
make format      # Auto-format code
```

## Docker Required

This project uses Docker to ensure consistent behavior across all environments. If you don't have Docker:

1. Install from: https://docs.docker.com/get-docker/
2. Start Docker
3. Run `make check` to verify

## Troubleshooting

### Gateway won't start
- Check Docker is running: `docker info`
- Check logs: `make logs`
- Verify .env file exists and has your API key

### OpenAI API errors
- Verify your API key is valid: `echo $OPENAI_API_KEY`
- Check the key starts with `sk-` and is not the placeholder
- Ensure you have API credits at https://platform.openai.com/usage

### Port conflicts
- If port 4000 is in use, change it in .env:
  ```bash
  SOLSTICE_GATEWAY_PORT=4001
  ```

### Test the full setup
```bash
# This script verifies everything is working
./scripts/test-gateway.sh
```