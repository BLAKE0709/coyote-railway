# 🐺 COYOTE FINAL DEPLOYMENT CHECKLIST

## ✅ Pre-Deployment (Claude Code did this)
- [x] Code complete (24 files)
- [x] 13 tools implemented
- [x] Git pushed to GitHub
- [x] Google credentials combiner ready
- [x] All env vars documented

---

## 👤 Your Tasks (10-15 minutes)

### Step 1: Open Railway Dashboard (2 min)
- Go to: https://railway.app/dashboard
- Click your COYOTE project (or create new one)
- If new: "New Project" → "Deploy from GitHub" → `BLAKE0709/coyote-railway`

### Step 2: Add Environment Variables (5 min)
Click "Variables" tab and add each:

**Get values from:**
- `~/coyote-railway/KEYS.txt`
- `~/coyote-railway/.env`

**Required variables:**
```
ANTHROPIC_API_KEY=<see ~/coyote-railway/.env>
VONAGE_API_KEY=<see ~/coyote-railway/.env>
VONAGE_API_SECRET=<see ~/coyote-railway/.env>
VONAGE_PHONE_NUMBER=+19498177088
```

Note: The actual values are in your local `~/.env` file. Copy them from there.

**Optional (for Google integration):**
```
GOOGLE_CREDENTIALS_JSON={"token":"...","refresh_token":"...","client_id":"...","client_secret":"..."}
```
*Get this from: `~/coyote-railway/GOOGLE_CREDENTIALS_JSON.txt` (after running combiner)*

**Optional (for revenue tracking):**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
```

Railway will auto-redeploy after adding variables (~1-2 minutes)

### Step 3: Verify Webhook URL (2 min)

1. Go to Vonage Dashboard: https://dashboard.nexmo.com
2. Find your Application or Number settings
3. Set **Inbound Webhook URL** to:
   ```
   https://coyote-railway-production.up.railway.app/webhook/inbound
   ```
   *(Replace with your actual Railway URL)*
4. Set method to **POST**
5. Click **Save**

### Step 4: Test Basic Functionality (3 min)

Text **+1 949-817-7088** with:
- ✅ `status` → Should respond with system status
- ✅ `hello` → Should have a conversation
- ⏳ `emails` → Will say "Gmail not configured" without Google creds
- ⏳ `schedule` → Will say "Calendar not configured" without Google creds

### Step 5: Add Google Integration (Optional - 10 min)

**If you don't have Google credentials yet:**
1. Go to: https://console.cloud.google.com
2. Create new project: "COYOTE-Chief-of-Staff"
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
4. Create OAuth 2.0 credentials:
   - Application type: **Desktop app**
   - Download as `credentials.json`
5. Run OAuth flow to get `token.json`
   - Use any Google API Python quickstart
   - Or use a library like `google-auth-oauthlib`

**If you have credentials:**
1. Put files in one of these locations:
   - `~/coyote/config/google-credentials.json`
   - `~/coyote-railway/google-credentials.json`
2. Put token in:
   - `~/coyote/config/google-token.json`
   - `~/coyote-railway/google-token.json`
3. Run combiner:
   ```bash
   cd ~/coyote-railway
   python combine_google_creds.py
   ```
4. Copy output to Railway variable: `GOOGLE_CREDENTIALS_JSON`
5. Railway will auto-redeploy

### Step 6: Test Full Functionality (2 min)

With Google credentials added, text:
- ✅ `emails` → Should show unread count and recent emails
- ✅ `schedule` → Should show today's calendar
- ✅ `next meeting` → Should show next upcoming event
- ✅ `search emails from john` → Should search Gmail

---

## 🎯 Success Criteria

### Minimum (No Google):
- [ ] SMS `status` gets response
- [ ] SMS `hello` has conversation
- [ ] Health endpoint works: `https://your-app.railway.app/health`

### Full (With Google):
- [ ] SMS `emails` shows inbox
- [ ] SMS `schedule` shows calendar
- [ ] SMS `search emails [query]` works

---

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `~/coyote-railway/KEYS.txt` | All API keys for Railway |
| `~/coyote-railway/.env` | Local environment (same keys) |
| `~/coyote-railway/GOOGLE_CREDENTIALS_JSON.txt` | Google creds (after running combiner) |
| `~/coyote-railway/RAILWAY_GOOGLE_SETUP.txt` | Google setup instructions |
| `~/coyote-railway/combine_google_creds.py` | Credential combiner script |
| `~/coyote-railway/DEPLOY_NOW.md` | Quick deployment guide |

---

## 🆘 Troubleshooting

### SMS not responding
- Check Railway logs for incoming webhooks
- Verify Vonage webhook URL is correct
- Test health endpoint first
- Check environment variables are set

### "Gmail not configured"
- GOOGLE_CREDENTIALS_JSON variable missing or incorrect
- Run combiner script and update Railway variable
- Check Railway logs for specific error

### "Token expired"
- Google token needs refresh
- Regenerate token.json
- Re-run combiner script
- Update Railway variable

### Railway build fails
- Check Railway logs
- Verify all files pushed to GitHub
- Check requirements.txt syntax

---

## 📊 Monitoring

**Railway Dashboard:**
- Logs: Real-time application logs
- Metrics: CPU, memory, requests
- Deployments: History and status

**Health Check:**
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "integrations": {
    "anthropic": true,
    "vonage": true,
    "google": true/false,
    "supabase": false
  }
}
```

---

## 🚀 Quick Reference

**Railway:** https://railway.app/dashboard
**Vonage:** https://dashboard.nexmo.com
**Google Cloud:** https://console.cloud.google.com
**GitHub Repo:** https://github.com/BLAKE0709/coyote-railway
**SMS Number:** +1 949-817-7088

---

## ✅ Final Checklist

- [ ] Railway project created/connected
- [ ] All environment variables added
- [ ] Vonage webhook configured
- [ ] SMS test passes
- [ ] Google integration added (optional)
- [ ] Full SMS tests pass

---

🐺 **Time to completion: 10-15 minutes**
📖 **Need help? See:** `DEPLOY_NOW.md` or `MISSION_COMPLETE.md`
