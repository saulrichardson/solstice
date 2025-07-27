# API Key Configuration

This project uses centralized OpenAI API key management to ensure consistent configuration across all modules.

## How It Works

1. **Central Configuration**: All OpenAI API keys are managed through `src/gateway/app/openai_client.py`
2. **Ignores Shell Variables**: The system explicitly ignores `OPENAI_API_KEY` set in your shell environment
3. **Uses .env File**: API keys are loaded exclusively from the `.env` file in the project root

## Benefits

- **No Shell Conflicts**: No more issues with shell startup files overriding project settings
- **Consistent Configuration**: All modules use the same API key configuration
- **Easy Testing**: Different projects can use different API keys without conflicts
- **Security**: API keys are project-specific and not exposed in shell history

## Usage

1. Set your API key in `.env`:
   ```
   OPENAI_API_KEY=sk-proj-your-api-key-here
   ```

2. Import the centralized client:
   ```python
   from src.gateway.app.openai_client import get_async_openai_client
   
   client = get_async_openai_client()
   ```

3. The client will automatically use the API key from `.env`, ignoring any shell environment variables

## Testing

Run the configuration test to verify everything is working:
```bash
python test_central_config.py
```

This will verify:
- API key is loaded from .env (not shell)
- All modules use the centralized configuration
- Client instances are properly shared (singleton pattern)