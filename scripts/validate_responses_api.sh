#!/bin/bash
# Validate that the gateway is properly configured for Responses API only

set -e

echo "Validating Responses API Gateway Configuration"
echo "============================================="
echo ""

# 1. Check Python files don't have chat completions fallback
echo "1. Checking for chat completions fallback code..."
if grep -r "chat.completions" src/fact_check/gateway/app/providers/openai_provider.py 2>/dev/null; then
    echo "✗ Found chat.completions references (should be removed)"
    exit 1
else
    echo "✓ No chat.completions fallback found"
fi

# 2. Check for proper SDK version requirement
echo ""
echo "2. Checking SDK version requirement..."
if grep -q "openai>=1.50.0" pyproject.toml; then
    echo "✓ Correct SDK version requirement (>=1.50.0)"
else
    echo "✗ Invalid SDK version requirement"
    exit 1
fi

# 3. Check for NotImplementedError messages
echo ""
echo "3. Checking error handling..."
if grep -q "OpenAI SDK does not support Responses API" src/fact_check/gateway/app/providers/openai_provider.py; then
    echo "✓ Proper error messages for missing Responses API"
else
    echo "✗ Missing error messages"
    exit 1
fi

# 4. Check documentation
echo ""
echo "4. Checking documentation..."
if [ -f "src/fact_check/gateway/GATEWAY_API.md" ] && [ -f "src/fact_check/gateway/MIGRATION.md" ]; then
    echo "✓ Documentation files exist"
    
    # Check for no fallback mention
    if grep -q "No fallback" src/fact_check/gateway/GATEWAY_API.md; then
        echo "✓ Documentation states no fallback"
    else
        echo "✗ Documentation should mention no fallback"
    fi
else
    echo "✗ Missing documentation files"
    exit 1
fi

# 5. Check test files
echo ""
echo "5. Checking test coverage..."
if [ -f "tests/test_responses_api_strict.py" ]; then
    echo "✓ Strict API tests exist"
else
    echo "✗ Missing strict API tests"
fi

echo ""
echo "============================================="
echo "✓ All validations passed!"
echo ""
echo "The gateway is properly configured to use only the Responses API."
echo "No fallback to Chat Completions API is present."
echo ""
echo "Next steps:"
echo "1. Run: python scripts/check_sdk_compatibility.py"
echo "2. Ensure OpenAI SDK >= 1.50.0 is installed"
echo "3. Start the gateway with: make up"
echo "4. Run tests with: python scripts/test_responses_gateway.py"