import asyncio
import json
from src.gateway.app.openai_client import get_async_openai_client

async def test_responses_api():
    client = get_async_openai_client()
    
    # Test with a simple request
    response = await client.responses.create(
        model="gpt-4.1",
        input="What is 2+2?",
        temperature=0.0
    )
    
    # Print the full response
    response_dict = response.model_dump()
    print("Full response structure:")
    print(json.dumps(response_dict, indent=2))
    
    # Check usage specifically
    if "usage" in response_dict:
        print("\nUsage data:")
        print(json.dumps(response_dict["usage"], indent=2))
    else:
        print("\nNo usage data in response")

if __name__ == "__main__":
    asyncio.run(test_responses_api())