#!/usr/bin/env python
"""Check your setup and API key."""
import os
from dotenv import load_dotenv

print("🔍 Checking your setup...\n")

# Load .env file
load_dotenv()

# Check API key
api_key = os.getenv("OPENAI_API_KEY", "")

print("1. API Key Check:")
if not api_key:
    print("   ❌ No API key found in environment")
    print("   → Create a .env file with: OPENAI_API_KEY=your-key-here")
elif not api_key.startswith("sk-"):
    print("   ❌ API key doesn't start with 'sk-'")
    print("   → Make sure you copied the full key from OpenAI")
else:
    print(f"   ✅ API key found (length: {len(api_key)})")
    print(f"   → Key starts with: {api_key[:7]}...")
    print(f"   → Key ends with: ...{api_key[-4:]}")

print("\n2. Testing API Key with OpenAI:")
try:
    import openai
    client = openai.OpenAI(api_key=api_key)
    
    # Try to list models (cheap API call)
    models = client.models.list()
    print("   ✅ API key is valid! Connected to OpenAI successfully.")
    
    # Show available models
    print("\n3. Available models:")
    model_names = [m.id for m in models if 'gpt' in m.id or 'o1' in m.id]
    for model in sorted(model_names)[:10]:
        print(f"   - {model}")
    
except openai.AuthenticationError as e:
    print(f"   ❌ Invalid API key: {str(e).split('.')[0]}")
    print("\n   To fix this:")
    print("   1. Go to https://platform.openai.com/api-keys")
    print("   2. Create a new API key")
    print("   3. Update your .env file with the new key")
    
except Exception as e:
    print(f"   ❌ Error: {type(e).__name__}: {e}")

print("\n📝 Next steps:")
print("1. Make sure you have a valid OpenAI API key")
print("2. Update your .env file with: OPENAI_API_KEY=sk-...")
print("3. Run this script again to verify")
print("4. Then run: python test_direct.py")