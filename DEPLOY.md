# 🚀 COYOTE Deployment Guide

Complete deployment instructions for Railway.

---

## ✅ PHASE 1: VERIFY LOCAL FILES

```bash
cd ~/coyote-railway
ls -la
```

**Expected files:**
- main.py (FastAPI app)
- config.py (environment config)
- claude_handler.py (Claude + tools)
- tools/ (gmail, calendar, drive, swarm, revenue)
- utils/ (combine_creds.py)
- requirements.txt
- Procfile
- railway.toml
- README.md

---

## ✅ PHASE 2: GOOGLE CREDENTIALS

### Option A: If you have Google credentials files

```bash
cd ~/coyote-railway
python utils/combine_creds.py /path/to/credentials.json /path/to/token.json
```

This creates `GOOGLE_CREDENTIALS_JSON.txt` with the combined JSON.

### Option B: If you need to create Google credentials

1. Go to https://console.cloud.google.com
2. Create a project or select existing
3. Enable APIs: Gmail API, Calendar API, Drive API
4. Create OAuth 2.0 credentials
5. Download credentials.json
6. Run OAuth flow to get token.json
7. Run combine_creds.py

---

## ✅ PHASE 3: TEST LOCALLY (Optional)

```bash
cd ~/coyote-railway

# Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_CREDENTIALS_JSON={"token":"...paste from combine_creds..."}
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx
VONAGE_PHONE_NUMBER=+1234567890
EOF

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --port 8000

# In another terminal, test endpoints:
curl http://localhost:8000/health
curl -X POST http://localhost:8000/test -H "Content-Type: application/json" -d '{"message": "status"}'
```

---

## ✅ PHASE 4: COMMIT & PUSH TO GITHUB

```bash
cd ~/coyote-railway

git add .
git status

git commit -m "Full COYOTE Chief of Staff: Gmail, Calendar, Drive, Swarm, Revenue

Complete SMS-based AI chief of staff with:
- Gmail search, read, send
- Calendar view, create events
- Drive search
- Swarm status monitoring
- Revenue tracking (Supabase)
- Claude tool use with 13 tools
- Vonage SMS webhook
- FastAPI with health checks
- Test endpoints

Ready for Railway deployment.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

---

## ✅ PHASE 5: RAILWAY DEPLOYMENT

### 5.1 Connect to Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `BLAKE0709/coyote-railway`
5. Railway will auto-detect Python and deploy

### 5.2 Add Environment Variables

In Railway dashboard, go to Variables tab and add:

**Required:**
```
ANTHROPIC_API_KEY=sk-ant-xxx
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx
VONAGE_PHONE_NUMBER=+1234567890
```

**Google (from combine_creds.py output):**
```
GOOGLE_CREDENTIALS_JSON={"token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}
```

**Optional (if you have Supabase):**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
```

**Optional (if Swarm API deployed separately):**
```
SWARM_API_URL=https://your-swarm-api.railway.app
```

### 5.3 Deploy

Railway will automatically deploy after adding variables. Wait for build to complete.

---

## ✅ PHASE 6: CONFIGURE VONAGE WEBHOOK

1. Get your Railway URL: `https://coyote-railway-production.up.railway.app`
2. Go to Vonage Dashboard
3. Navigate to your SMS API settings
4. Set **Inbound Webhook URL** to:
   ```
   https://your-app.railway.app/webhook/inbound
   ```
5. Set method to **POST**
6. Save

---

## ✅ PHASE 7: TEST VIA SMS

Send SMS to your Vonage number:

**Test Commands:**
- `status` → Should reply with COYOTE response
- `emails` → Check unread count (if Google configured)
- `schedule` → Today's calendar
- `next meeting` → Next event
- `revenue` → Revenue summary (if Supabase configured)
- `swarm status` → Swarm systems status

---

## ✅ PHASE 8: TEST VIA API

```bash
# Get your Railway URL
RAILWAY_URL="https://your-app.railway.app"

# Health check
curl $RAILWAY_URL/health

# Test endpoint (no SMS)
curl -X POST $RAILWAY_URL/test \
  -H "Content-Type: application/json" \
  -d '{"message": "what is my schedule today?"}'

# Test with different queries
curl -X POST $RAILWAY_URL/test \
  -H "Content-Type: application/json" \
  -d '{"message": "revenue"}'

curl -X POST $RAILWAY_URL/test \
  -H "Content-Type: application/json" \
  -d '{"message": "search emails from martin marietta"}'
```

---

## 🎯 SUCCESS CRITERIA

- [ ] Health endpoint returns 200 with integration status
- [ ] Test endpoint responds without errors
- [ ] SMS commands trigger responses
- [ ] Gmail tools work (if configured)
- [ ] Calendar tools work (if configured)
- [ ] Revenue tools work (if Supabase configured)
- [ ] Claude tool use executes correctly
- [ ] SMS responses under 160 chars

---

## 🔧 TROUBLESHOOTING

### Railway build fails
- Check `requirements.txt` syntax
- Ensure Python 3.10+ in Railway settings
- Check Railway logs for errors

### SMS not responding
- Verify Vonage webhook URL is correct
- Check Railway logs for incoming requests
- Test `/test` endpoint directly first

### Google APIs not working
- Verify `GOOGLE_CREDENTIALS_JSON` is valid JSON (no newlines!)
- Check token hasn't expired
- Verify APIs are enabled in Google Cloud Console
- Check Railway logs for auth errors

### Claude errors
- Verify `ANTHROPIC_API_KEY` is correct
- Check API key has sufficient credits
- Look for rate limit errors in logs

---

## 📊 MONITORING

Railway provides:
- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, network usage
- **Deployments**: History of all deploys

Access via Railway dashboard.

---

## 🔄 UPDATES

To deploy updates:

```bash
cd ~/coyote-railway
# Make changes to code
git add .
git commit -m "Update description"
git push origin main
```

Railway will auto-deploy on push to main.

---

## 🐺 COYOTE IS LIVE!

Once deployed, COYOTE is accessible 24/7 via SMS. Blake can text commands and get instant responses powered by Claude with full access to Gmail, Calendar, Drive, Swarm status, and revenue data.
