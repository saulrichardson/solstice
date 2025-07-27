#!/usr/bin/env python
"""Simple test script to verify the gateway works with OpenAI."""
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gateway():
    """Make a simple request to the gateway and print the response."""
    async with httpx.AsyncClient() as client:
        print("🚀 Sending request to gateway...")
        
        response = await client.post(
            "http://localhost:8000/v1/responses",
            json={
                "model": "gpt-4o-mini",
                "input": "Say 'Hello! The gateway is working!' in a cheerful way.",
                "temperature": 0.7
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success! Response from OpenAI:")
            print("-" * 50)
            
            # Extract the text from the response
            if data.get("output") and len(data["output"]) > 0:
                text = data["output"][0].get("text", "")
                print(text)
            else:
                print("No output text found")
            
            print("-" * 50)
            print(f"\n📊 Token usage:")
            print(f"  - Input tokens: {data.get('input_tokens', 0)}")
            print(f"  - Output tokens: {data.get('output_tokens', 0)}")
            print(f"  - Total tokens: {data['usage']['total_tokens']}")
            print(f"\n🆔 Response ID: {data.get('id', 'N/A')}")
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    print("Testing Solstice Gateway with OpenAI...\n")
    asyncio.run(test_gateway())