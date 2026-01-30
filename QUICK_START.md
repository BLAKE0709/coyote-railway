# ⚡ QUICK START - Deploy COYOTE in 20 Minutes

## 🎯 What You're Deploying

A full AI Chief of Staff accessible via SMS with:
- Gmail, Calendar, Drive integration
- Swarm status monitoring
- Revenue tracking
- 13 Claude tools

---

## ✅ Step 1: Local Test (2 minutes)

API keys are already in `.env` file!

```bash
cd ~/coyote-railway

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --port 8000
```

Open browser to http://localhost:8000 - should see:
```json
{"status": "COYOTE is alive", "integrations": {...}}
```

**Test without SMS:**
```bash
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"message": "status"}'
```

Stop server: `Ctrl+C`

---

## ✅ Step 2: Deploy to Railway (5 minutes)

### Via Railway Dashboard:

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `BLAKE0709/coyote-railway`
5. Railway auto-detects and builds

### Via Railway CLI (faster):

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
cd ~/coyote-railway
railway init
railway up

# Set environment variables (see KEYS.txt for actual values)
railway variables set ANTHROPIC_API_KEY=sk-ant-xxx
railway variables set VONAGE_API_KEY=xxx
railway variables set VONAGE_API_SECRET=xxx
railway variables set VONAGE_PHONE_NUMBER=+1xxx

# Get your URL
railway domain
```

Your app will be at: `https://coyote-railway-production.up.railway.app`

---

## ✅ Step 3: Configure Vonage (2 minutes)

1. Go to https://dashboard.nexmo.com
2. Find your Vonage number: `+19498177088`
3. Click on the number to configure
4. Set **Inbound Webhook URL**:
   ```
   https://your-railway-url.up.railway.app/webhook/inbound
   ```
5. Set method to **POST**
6. Save

---

## ✅ Step 4: Test via SMS (1 minute)

Text your Vonage number: `+19498177088`

**Try these:**
- `status` → Should get COYOTE response
- `hello` → Should get greeting
- `revenue` → Should get revenue summary (needs Supabase)
- `swarm status` → Should get swarm info (needs Swarm API)

Without Google configured:
- `emails` → Will say "Gmail not configured"
- `schedule` → Will say "Calendar not configured"

---

## ✅ Step 5: Add Google Integration (10 minutes - OPTIONAL)

### Find Existing Credentials

```bash
# Search for Google credentials
find ~ -name "*google*credentials*.json" -o -name "*google*token*.json" 2>/dev/null
```

### Or Create New Credentials

1. Go to https://console.cloud.google.com
2. Create project: "COYOTE"
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download `credentials.json`
5. Run OAuth flow to get `token.json`
6. Combine credentials:

```bash
cd ~/coyote-railway
python utils/combine_creds.py /path/to/credentials.json /path/to/token.json
```

This outputs the combined JSON. Copy it.

7. Add to Railway:

```bash
# Via CLI
railway variables set GOOGLE_CREDENTIALS_JSON='{"token":"...paste here..."}'

# Or via Dashboard: Variables tab → Add Variable
```

8. Railway will auto-redeploy with Google access

---

## 🎯 Testing Checklist

### API Tests (no SMS needed)

```bash
RAILWAY_URL="https://your-app.railway.app"

# Health check
curl $RAILWAY_URL/health

# Test basic message
curl -X POST $RAILWAY_URL/test -H "Content-Type: application/json" -d '{"message": "hello"}'

# Test without Google configured
curl -X POST $RAILWAY_URL/test -H "Content-Type: application/json" -d '{"message": "emails"}'
```

### SMS Tests

Text to `+19498177088`:
- ✅ `status`
- ✅ `hello`
- ⏳ `emails` (needs Google)
- ⏳ `schedule` (needs Google)
- ⏳ `revenue` (needs Supabase)

---

## 🐺 SUCCESS!

You now have a fully deployed AI Chief of Staff accessible via SMS!

**What works NOW (without Google):**
- ✅ SMS webhook handling
- ✅ Claude conversation
- ✅ Basic commands
- ✅ Swarm status (if Swarm API configured)
- ✅ Revenue (if Supabase configured)

**What needs Google credentials:**
- ⏳ Gmail search, read, send
- ⏳ Calendar view, create
- ⏳ Drive search

**Next Steps:**
1. Add Google credentials for full functionality
2. Add Supabase for revenue tracking
3. Configure Swarm API URL
4. Customize system prompt in `claude_handler.py`

---

## 📊 Monitoring

**Railway Dashboard:**
- Logs: See all SMS messages and responses
- Metrics: CPU, memory, requests
- Deployments: Auto-deploy on git push

**Health Check:**
```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "integrations": {
    "anthropic": true,
    "vonage": true,
    "google": false,
    "supabase": false
  }
}
```

---

## 🔧 Quick Fixes

**SMS not working:**
- Check Railway logs for incoming webhook
- Verify Vonage webhook URL is correct
- Test `/test` endpoint directly

**"Gmail not configured":**
- Add `GOOGLE_CREDENTIALS_JSON` to Railway variables
- See Step 5 above

**Slow responses:**
- Railway free tier has cold starts (~2-3s)
- Upgrade to Pro for instant responses

---

## 🚀 You're Live!

COYOTE is now running 24/7 on Railway, accessible via SMS at `+19498177088`.

**Repository:** https://github.com/BLAKE0709/coyote-railway
**Railway:** https://railway.app
**Vonage:** https://dashboard.nexmo.com

🐺 **Time to hunt.**
