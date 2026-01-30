#!/bin/bash
# Local testing script for COYOTE

echo "🐺 COYOTE Local Test Suite"
echo "================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ No .env file found!"
    echo "Create .env from .env.example and add your keys"
    exit 1
fi

# Source env vars
export $(cat .env | grep -v '^#' | xargs)

# Check required vars
echo "Checking environment variables..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set"
    exit 1
fi
echo "✅ ANTHROPIC_API_KEY set"

if [ -z "$VONAGE_API_KEY" ]; then
    echo "⚠️  VONAGE_API_KEY not set (optional for local testing)"
fi

if [ -z "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "⚠️  GOOGLE_CREDENTIALS_JSON not set (Google tools won't work)"
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Start server in background
echo ""
echo "Starting server on port 8000..."
uvicorn main:app --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test endpoints
echo ""
echo "Testing endpoints..."
echo ""

echo "1️⃣ Health check:"
curl -s http://localhost:8000/health | python -m json.tool
echo ""

echo "2️⃣ Root status:"
curl -s http://localhost:8000 | python -m json.tool
echo ""

echo "3️⃣ Test basic message:"
curl -s -X POST http://localhost:8000/test \
    -H "Content-Type: application/json" \
    -d '{"message": "hello"}' | python -m json.tool
echo ""

echo "4️⃣ Test calendar query:"
curl -s -X POST http://localhost:8000/test \
    -H "Content-Type: application/json" \
    -d '{"message": "what is on my schedule today?"}' | python -m json.tool
echo ""

echo "5️⃣ Test email query:"
curl -s -X POST http://localhost:8000/test \
    -H "Content-Type: application/json" \
    -d '{"message": "how many unread emails?"}' | python -m json.tool
echo ""

echo "6️⃣ Test revenue query:"
curl -s -X POST http://localhost:8000/test \
    -H "Content-Type: application/json" \
    -d '{"message": "revenue"}' | python -m json.tool
echo ""

echo "7️⃣ Test swarm status:"
curl -s -X POST http://localhost:8000/test \
    -H "Content-Type: application/json" \
    -d '{"message": "swarm status"}' | python -m json.tool
echo ""

# Kill server
echo "Stopping server..."
kill $SERVER_PID

echo ""
echo "✅ Tests complete!"
echo ""
echo "To run server manually:"
echo "  uvicorn main:app --reload --port 8000"
