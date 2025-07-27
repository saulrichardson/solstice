#!/usr/bin/env python
"""Direct test of OpenAI provider without the gateway."""
import asyncio

from dotenv import load_dotenv

from src.gateway.app.providers.base import ResponseRequest
from src.gateway.app.providers.openai_provider import OpenAIProvider

# Load environment variables
load_dotenv()


async def test_openai_direct():
    """Test OpenAI provider directly."""
    try:
        # Create provider
        provider = OpenAIProvider()
        print("✅ OpenAI provider initialized")

        # Create a simple request
        request = ResponseRequest(
            model="gpt-4o-mini",
            input="What is 2+2? Answer with just the number.",
            temperature=0,
        )

        print("🚀 Sending request to OpenAI...")
        response = await provider.create_response(request)

        print("\n✅ Success! Response from OpenAI:")
        print("-" * 50)

        # Debug: print the full response
        print(f"Response ID: {response.id}")
        print(f"Model: {response.model}")
        print(f"Output: {response.output}")

        # Extract the text
        if response.output and len(response.output) > 0:
            text = response.output[0].get("text", "")
            print(f"Answer: {text}")
        else:
            print("⚠️  No output found in response")

        print("-" * 50)
        print("\n📊 Token usage:")
        print(f"  - Input tokens: {response.input_tokens}")
        print(f"  - Output tokens: {response.output_tokens}")
        print(
            f"  - Total tokens: {response.usage.get('total_tokens', 0) if response.usage else 0}"
        )

        # Debug: print full response object
        print("\n🔍 Full response object:")
        print(response)

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        print("\nMake sure you have a valid OPENAI_API_KEY in your .env file")


if __name__ == "__main__":
    print("Testing OpenAI Provider Directly...\n")
    asyncio.run(test_openai_direct())
