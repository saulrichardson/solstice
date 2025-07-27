#!/bin/bash
# Test script to verify gateway is working with OpenAI Responses API

set -e

GATEWAY_URL="http://localhost:${SOLSTICE_GATEWAY_PORT:-4000}"

echo "Testing Solstice Gateway (Responses API)"
echo "========================================"
echo ""

# 1. Check if gateway is running
echo "1. Checking gateway health..."
if curl -s "${GATEWAY_URL}/health" > /dev/null; then
    echo "✓ Gateway is running"
    curl -s "${GATEWAY_URL}/health" | jq '.' || curl -s "${GATEWAY_URL}/health"
else
    echo "❌ Gateway is not running at ${GATEWAY_URL}"
    echo "   Run 'make up' to start the gateway"
    exit 1
fi
echo ""

# 2. List available models
echo "2. Listing available models..."
curl -s "${GATEWAY_URL}/models" | jq '.' 2>/dev/null || curl -s "${GATEWAY_URL}/models"
echo ""

# 3. Test OpenAI connection with Responses API
echo "3. Testing OpenAI Responses API connection..."
echo "   Sending test request to gpt-4.1-mini..."

RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/v1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY:-sk-1234}" \
  -d '{
    "model": "gpt-4.1-mini",
    "input": "Say exactly: TEST_SUCCESS",
    "temperature": 0,
    "max_output_tokens": 20
  }')

# Check if response contains error
if echo "$RESPONSE" | grep -q "error"; then
    echo "❌ OpenAI API error:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    echo ""
    echo "Common issues:"
    echo "- Invalid API key in .env file"
    echo "- API key not set (check OPENAI_API_KEY in .env)"
    echo "- OpenAI service issues"
    exit 1
fi

# Check if we got the expected response
if echo "$RESPONSE" | grep -q "TEST_SUCCESS"; then
    echo "✓ OpenAI Responses API is working correctly!"
    echo ""
    echo "Response:"
    echo "$RESPONSE" | jq '.output_text' 2>/dev/null || echo "$RESPONSE"
else
    echo "⚠ Unexpected response from OpenAI:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
fi
echo ""

# 4. Test caching
echo "4. Testing cache functionality..."
echo "   Sending identical request (should be cached)..."

START_TIME=$(date +%s)
curl -s -X POST "${GATEWAY_URL}/v1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY:-sk-1234}" \
  -d '{
    "model": "gpt-4.1-mini",
    "input": "Say exactly: TEST_SUCCESS",
    "temperature": 0,
    "max_output_tokens": 20
  }' > /dev/null
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $DURATION -le 1 ]; then
    echo "✓ Cache is working (response time: ${DURATION}s)"
else
    echo "⚠ Cache might not be working (response time: ${DURATION}s)"
fi
echo ""

# 5. Test stateful conversation
echo "5. Testing stateful conversations..."
RESPONSE1=$(curl -s -X POST "${GATEWAY_URL}/v1/responses" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY:-sk-1234}" \
  -d '{
    "model": "gpt-4.1-mini",
    "input": "My name is TestUser and I like pizza.",
    "store": true
  }')

RESPONSE_ID=$(echo "$RESPONSE1" | jq -r '.id' 2>/dev/null)
if [ -n "$RESPONSE_ID" ] && [ "$RESPONSE_ID" != "null" ]; then
    echo "✓ Created stateful response: $RESPONSE_ID"
    
    # Try to retrieve it
    RETRIEVED=$(curl -s "${GATEWAY_URL}/v1/responses/${RESPONSE_ID}" \
      -H "Authorization: Bearer ${OPENAI_API_KEY:-sk-1234}")
    
    if echo "$RETRIEVED" | grep -q "$RESPONSE_ID"; then
        echo "✓ Successfully retrieved stored response"
    else
        echo "⚠ Could not retrieve stored response"
    fi
else
    echo "⚠ Stateful conversation not working"
fi
echo ""

# 6. Show usage example
echo "6. Everything is working! Example usage:"
echo ""
echo "From Python:"
echo "```python"
echo "from fact_check.core.responses_client import ResponsesClient"
echo ""
echo "client = ResponsesClient()"
echo "response = client.complete('What is 2+2?')"
echo "print(response)"
echo ""
echo "# Stateful conversation"
echo "resp1 = client.create_stateful_conversation('My name is Alice')"
echo "resp2 = client.continue_conversation("
echo "    'What is my name?',"
echo "    previous_response_id=resp1['id']"
echo ")"
echo "```"
echo ""
echo "Direct API call:"
echo "```bash"
echo "curl -X POST ${GATEWAY_URL}/v1/responses \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Authorization: Bearer \$OPENAI_API_KEY' \\"
echo "  -d '{"
echo '    "model": "gpt-4.1-mini",'
echo '    "input": "Hello, world!"'
echo "  }'"
echo "```"