#!/bin/bash
# Test Railway deployment

if [ -z "$1" ]; then
    echo "Usage: ./test_railway.sh <your-railway-url>"
    echo "Example: ./test_railway.sh https://coyote-railway-production.up.railway.app"
    exit 1
fi

RAILWAY_URL="$1"

echo "🐺 Testing COYOTE on Railway"
echo "URL: $RAILWAY_URL"
echo "================================"
echo ""

echo "1️⃣ Health check:"
curl -s "$RAILWAY_URL/health" | python -m json.tool
echo ""

echo "2️⃣ Root status:"
curl -s "$RAILWAY_URL" | python -m json.tool
echo ""

echo "3️⃣ Test basic message:"
curl -s -X POST "$RAILWAY_URL/test" \
    -H "Content-Type: application/json" \
    -d '{"message": "status"}' | python -m json.tool
echo ""

echo "4️⃣ Test schedule query:"
curl -s -X POST "$RAILWAY_URL/test" \
    -H "Content-Type: application/json" \
    -d '{"message": "schedule"}' | python -m json.tool
echo ""

echo "5️⃣ Test email query:"
curl -s -X POST "$RAILWAY_URL/test" \
    -H "Content-Type: application/json" \
    -d '{"message": "emails"}' | python -m json.tool
echo ""

echo "6️⃣ Test revenue:"
curl -s -X POST "$RAILWAY_URL/test" \
    -H "Content-Type: application/json" \
    -d '{"message": "revenue"}' | python -m json.tool
echo ""

echo "✅ Railway tests complete!"
echo ""
echo "If all tests passed, COYOTE is ready for SMS!"
echo "Configure Vonage webhook to: $RAILWAY_URL/webhook/inbound"
