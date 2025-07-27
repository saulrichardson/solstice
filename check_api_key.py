#!/usr/bin/env python3
"""Deep check of API key for any issues"""

import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('OPENAI_API_KEY')

print("API Key Analysis:")
print(f"Length: {len(key)}")
print(f"Encoded length: {len(key.encode())}")
print(f"Any non-ASCII: {any(ord(c) > 127 for c in key)}")
print(f"Any whitespace: {any(c.isspace() for c in key)}")
has_quotes = '"' in key or "'" in key
print(f"Has quotes: {has_quotes}")
print(f"Starts with BOM: {key.startswith(chr(0xFEFF))}")

# Check for common issues
if key != key.strip():
    print("WARNING: Key has leading/trailing whitespace!")
    
# Check each character
special_found = False
for i, c in enumerate(key):
    if ord(c) > 127 or c.isspace():
        print(f"Special char at position {i}: {repr(c)} (ord={ord(c)})")
        special_found = True
        
if not special_found:
    print("No special characters found")

# Try manually with curl
print("\nTo test manually, try this curl command:")
print(f"""curl https://api.openai.com/v1/models \\
  -H "Authorization: Bearer {key}" """)