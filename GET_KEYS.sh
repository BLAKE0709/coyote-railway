#!/bin/bash
# Display API keys for Railway deployment
# Run: bash GET_KEYS.sh

echo "════════════════════════════════════════════════════════════════"
echo "🔑 RAILWAY ENVIRONMENT VARIABLES"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Copy these to Railway Dashboard > Variables:"
echo ""

if [ -f ~/.coyote-railway/.env ] || [ -f ~/coyote-railway/.env ]; then
    echo "From .env file:"
    echo "────────────────────────────────────────────────────────────────"
    cat ~/coyote-railway/.env 2>/dev/null || cat ~/.coyote-railway/.env 2>/dev/null
    echo "────────────────────────────────────────────────────────────────"
else
    echo "📋 Add these variables to Railway:"
    echo "────────────────────────────────────────────────────────────────"
    echo "ANTHROPIC_API_KEY=<your-key>"
    echo "VONAGE_API_KEY=<your-key>"
    echo "VONAGE_API_SECRET=<your-secret>"
    echo "VONAGE_PHONE_NUMBER=+19498177088"
    echo "────────────────────────────────────────────────────────────────"
    echo ""
    echo "⚠️  .env file not found. Check ~/coyote-railway/.env"
fi

echo ""
echo "📋 Optional (for Google integration):"
echo "────────────────────────────────────────────────────────────────"
if [ -f ~/coyote-railway/GOOGLE_CREDENTIALS_JSON.txt ]; then
    echo "GOOGLE_CREDENTIALS_JSON="
    cat ~/coyote-railway/GOOGLE_CREDENTIALS_JSON.txt
else
    echo "GOOGLE_CREDENTIALS_JSON=<run combine_google_creds.py first>"
fi
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "🚀 Add to Railway:"
echo "   1. Go to: https://railway.app/dashboard"
echo "   2. Click your project > Variables"
echo "   3. Add each variable above"
echo ""
echo "════════════════════════════════════════════════════════════════"
