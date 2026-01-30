# 🐺 COYOTE - AI Chief of Staff

Full chief of staff accessible via SMS.

## Features

- **Gmail**: Search, read, send emails
- **Calendar**: View today/upcoming, create events
- **Drive**: Search files
- **Swarm Status**: Monitor Prophet, Hydra, etc.
- **Revenue**: Today, MTD, MRR tracking

## SMS Commands

| Text | Response |
|------|----------|
| emails | Unread count + recent subjects |
| search emails [query] | Find specific emails |
| schedule | Today's calendar |
| next meeting | Next event |
| revenue | Today/MTD/MRR |
| swarm status | All systems status |

## Deployment

1. Push to GitHub
2. Connect Railway to repo
3. Add environment variables:
   - ANTHROPIC_API_KEY
   - VONAGE_API_KEY
   - VONAGE_API_SECRET
   - VONAGE_PHONE_NUMBER
   - GOOGLE_CREDENTIALS_JSON (run utils/combine_creds.py to generate)
   - SUPABASE_URL (optional)
   - SUPABASE_KEY (optional)

4. Set Vonage webhook to: https://your-app.railway.app/webhook/inbound

## Local Testing

```bash
export ANTHROPIC_API_KEY=xxx
export GOOGLE_CREDENTIALS_JSON='{"token":...}'
uvicorn main:app --reload

# Test
curl -X POST http://localhost:8000/test -H "Content-Type: application/json" -d '{"message": "schedule today"}'
```
