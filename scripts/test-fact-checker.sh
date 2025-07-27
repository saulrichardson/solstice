#!/bin/bash
# Test the fact-checker endpoint

PORT=${SOLSTICE_GATEWAY_PORT:-8000}
URL="http://localhost:${PORT}/v1/fact-check"

echo "Testing fact-checker at ${URL}..."

# Test data
CLAIM="The study showed that Drug-X reduced HbA1c levels by 1.2%"
DOCUMENT="Abstract:
This randomized controlled trial evaluated the efficacy of Drug-X in patients with type 2 diabetes.
Drug-X lowered HbA1c by 1.2 % (95 % CI -1.4 to -1.0) compared to placebo over 24 weeks.

Results:
Table 2 shows the primary outcomes:
- Drug-X group: HbA1c change = -1.23 % ± 0.11 %
- Placebo group: HbA1c change = -0.15 % ± 0.09 %"

# Make the request
RESPONSE=$(curl -s -X POST "${URL}" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg claim "$CLAIM" --arg doc "$DOCUMENT" '{claim: $claim, document_text: $doc}')")

if [ -z "$RESPONSE" ]; then
    echo "❌ No response from fact-checker. Is the gateway running?"
    exit 1
fi

# Check if response is valid JSON
if ! echo "$RESPONSE" | jq . >/dev/null 2>&1; then
    echo "❌ Invalid JSON response:"
    echo "$RESPONSE"
    exit 1
fi

# Extract verdict
VERDICT=$(echo "$RESPONSE" | jq -r '.verdict')
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

if [ "$SUCCESS" == "true" ]; then
    echo "✅ Fact-checker working!"
    echo "   Verdict: $VERDICT"
    echo "   Steps found: $(echo "$RESPONSE" | jq '.steps | length')"
else
    echo "❌ Fact-checker failed"
    echo "$RESPONSE" | jq .
    exit 1
fi