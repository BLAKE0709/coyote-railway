# 🚀 DEPLOY COYOTE NOW - COPY/PASTE GUIDE

Everything is ready. Follow these exact steps.

---

## 📋 BEFORE YOU START

You have:
- ✅ Code pushed to GitHub: `BLAKE0709/coyote-railway`
- ✅ API keys ready (see KEYS.txt)
- ✅ Test scripts ready
- ✅ Complete documentation

Time needed: **15-20 minutes**

---

## 🎯 STEP 1: DEPLOY TO RAILWAY (5 min)

### Option A: Railway CLI (Fastest)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Deploy
cd ~/coyote-railway
railway login
railway init
railway up

# Get your URL
railway domain
```

### Option B: Railway Dashboard

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `BLAKE0709/coyote-railway`
5. Wait for build (~3 minutes)

Your app URL: `https://coyote-railway-production.up.railway.app`

---

## 🔑 STEP 2: ADD ENVIRONMENT VARIABLES (5 min)

### Via Railway CLI:

```bash
# Get values from KEYS.txt file, then run:
railway variables set ANTHROPIC_API_KEY=<value-from-KEYS.txt>
railway variables set VONAGE_API_KEY=<value-from-KEYS.txt>
railway variables set VONAGE_API_SECRET=<value-from-KEYS.txt>
railway variables set VONAGE_PHONE_NUMBER=<value-from-KEYS.txt>
```

### Via Railway Dashboard:

1. Go to your project
2. Click "Variables" tab
3. Add each variable:
   - `ANTHROPIC_API_KEY` = (see KEYS.txt)
   - `VONAGE_API_KEY` = (see KEYS.txt)
   - `VONAGE_API_SECRET` = (see KEYS.txt)
   - `VONAGE_PHONE_NUMBER` = (see KEYS.txt)

Railway will auto-redeploy after adding variables.

---

## 🔗 STEP 3: CONFIGURE VONAGE WEBHOOK (2 min)

1. Go to https://dashboard.nexmo.com
2. Find number `+19498177088`
3. Click to configure
4. Set **Inbound Webhook URL**:
   ```
   https://your-railway-url.up.railway.app/webhook/inbound
   ```
   (Replace `your-railway-url` with actual Railway URL)
5. Set method: **POST**
6. Click **Save**

---

## ✅ STEP 4: TEST (3 min)

### Test 1: Health Check

```bash
RAILWAY_URL="https://your-railway-url.up.railway.app"
curl $RAILWAY_URL/health
```

Expected:
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

### Test 2: API Test

```bash
curl -X POST $RAILWAY_URL/test \
  -H "Content-Type: application/json" \
  -d '{"message": "hello"}'
```

Expected: JSON response with Claude's reply

### Test 3: SMS Test

Text `+19498177088`:
```
status
```

Expected: SMS reply from COYOTE

---

## 🎉 SUCCESS!

If all tests pass, COYOTE is LIVE!

**Working NOW:**
- ✅ SMS webhook
- ✅ Claude conversation
- ✅ Basic commands

**Needs Google credentials:**
- ⏳ Gmail, Calendar, Drive

**Optional:**
- ⏳ Supabase (revenue)
- ⏳ Swarm API (status)

---

## 📱 SMS COMMANDS TO TRY

Text to `+19498177088`:

**Basic:**
- `status`
- `hello`
- `help`

**Email (needs Google):**
- `emails`
- `unread emails`
- `search emails from john`

**Calendar (needs Google):**
- `schedule`
- `schedule today`
- `next meeting`

**Other (needs config):**
- `revenue`
- `swarm status`

---

## 🔧 ADD GOOGLE INTEGRATION (Optional - 10 min)

1. Find or create Google credentials
2. Run combiner:
   ```bash
   python utils/combine_creds.py credentials.json token.json
   ```
3. Copy output
4. Add to Railway:
   ```bash
   railway variables set GOOGLE_CREDENTIALS_JSON='{"token":"...paste..."}'
   ```

Railway auto-redeploys. Gmail/Calendar/Drive now work!

---

## 📊 MONITORING

**Railway Dashboard:**
- Logs: Real-time logs
- Metrics: CPU, memory, requests
- Deployments: History

**Health endpoint:**
```bash
curl https://your-railway-url.up.railway.app/health
```

---

## 🐺 YOU'RE LIVE!

COYOTE is running 24/7 on Railway at:
- **SMS:** +19498177088
- **URL:** https://your-railway-url.up.railway.app
- **Repo:** https://github.com/BLAKE0709/coyote-railway

Text the number to interact with your AI Chief of Staff!

---

## 🆘 TROUBLESHOOTING

**SMS not working:**
- Check Railway logs
- Verify Vonage webhook URL
- Test `/test` endpoint first

**"Gmail not configured":**
- Add GOOGLE_CREDENTIALS_JSON variable
- See "Add Google Integration" above

**Railway errors:**
- Check logs in Railway dashboard
- Verify all environment variables set
- Check health endpoint

**Need help:**
- Check DEPLOY.md for detailed guide
- Check MISSION_COMPLETE.md for full docs
- Check Railway logs for errors

---

## 📞 SUPPORT

Files with info:
- `QUICK_START.md` - Fast deployment guide
- `DEPLOY.md` - Detailed deployment steps
- `MISSION_COMPLETE.md` - Complete documentation
- `EXECUTION_SUMMARY.md` - Technical summary
- `README.md` - User guide
- `KEYS.txt` - API keys for Railway

All set! 🐺
