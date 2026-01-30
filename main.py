from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import os
from claude_handler import handle_message
from config import Config

app = FastAPI(title="COYOTE - AI Chief of Staff")

# Debug environment variables
print(f"🔍 ENV Check:")
print(f"  TWILIO_PHONE_NUMBER from os.getenv: {os.getenv('TWILIO_PHONE_NUMBER')}")
print(f"  TWILIO_PHONE_NUMBER from Config: {Config.TWILIO_PHONE_NUMBER}")
print(f"  All TWILIO vars: SID={bool(Config.TWILIO_ACCOUNT_SID)}, TOKEN={bool(Config.TWILIO_AUTH_TOKEN)}, PHONE={Config.TWILIO_PHONE_NUMBER}")

# Initialize Twilio SMS
twilio_client = None
try:
    from twilio.rest import Client
    if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
        print("🔧 Initializing Twilio SMS...")
        twilio_client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
        print("✅ Twilio SMS ready")
    else:
        print("⚠️ Twilio credentials missing")
except Exception as e:
    print(f"⚠️ Twilio SMS not available (app will still work): {e}")

@app.get("/")
def root():
    return {"status": "COYOTE is alive", "integrations": Config.validate()}

@app.get("/health")
def health():
    return {"status": "healthy", "integrations": Config.validate()}

@app.api_route("/webhook/inbound", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    """Handle incoming SMS from Twilio"""
    try:
        # Parse GET params, form data, or JSON
        if request.method == "GET":
            data = dict(request.query_params)
        elif "application/json" in request.headers.get("content-type", ""):
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        # Extract message details (Twilio uses From/Body, Vonage used msisdn/text)
        from_number = data.get("From") or data.get("msisdn") or data.get("from")
        text = data.get("Body") or data.get("text") or data.get("message", "")

        if not text:
            return PlainTextResponse("OK")

        print(f"📱 Incoming from {from_number}: {text}")

        # Process with Claude + tools
        response = handle_message(text)

        print(f"🐺 Response: {response}")

        # Send SMS reply via Twilio
        print(f"🔍 Debug: twilio_client={twilio_client is not None}, phone={Config.TWILIO_PHONE_NUMBER}")
        if twilio_client and Config.TWILIO_PHONE_NUMBER:
            try:
                message = twilio_client.messages.create(
                    body=response[:1600],  # Twilio handles segmentation, but let's be reasonable
                    from_=Config.TWILIO_PHONE_NUMBER,
                    to=from_number
                )
                print(f"✅ SMS sent to {from_number}")
                print(f"📊 Message SID: {message.sid}")
            except Exception as e:
                print(f"❌ SMS send error: {e}")
        else:
            print(f"⚠️ SMS sending disabled - Twilio not initialized")

        return PlainTextResponse("OK")

    except Exception as e:
        print(f"❌ Error: {e}")
        return PlainTextResponse("OK")

@app.post("/webhook/status")
async def status_webhook(request: Request):
    """Handle delivery receipts"""
    return PlainTextResponse("OK")

@app.post("/test")
async def test_message(request: Request):
    """Test endpoint - send a message without SMS"""
    try:
        data = await request.json()
        message = data.get("message", "status")
        response = handle_message(message)
        return {"input": message, "response": response}
    except Exception as e:
        return {"error": str(e)}

@app.get("/test/{message}")
async def test_get(message: str):
    """GET test endpoint"""
    response = handle_message(message)
    return {"input": message, "response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
