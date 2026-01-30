from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import os
from claude_handler import handle_message
from config import Config

app = FastAPI(title="COYOTE - AI Chief of Staff")

# Debug environment variables
print(f"🔍 ENV Check:")
print(f"  VONAGE_PHONE_NUMBER from os.getenv: {os.getenv('VONAGE_PHONE_NUMBER')}")
print(f"  VONAGE_PHONE_NUMBER from Config: {Config.VONAGE_PHONE_NUMBER}")
print(f"  All VONAGE vars: API_KEY={bool(Config.VONAGE_API_KEY)}, SECRET={bool(Config.VONAGE_API_SECRET)}, PHONE={Config.VONAGE_PHONE_NUMBER}")

# Initialize Vonage SMS
vonage_client = None
try:
    from vonage import Vonage, Auth
    if Config.VONAGE_API_KEY and Config.VONAGE_API_SECRET:
        print("🔧 Initializing Vonage SMS...")
        auth = Auth(api_key=Config.VONAGE_API_KEY, api_secret=Config.VONAGE_API_SECRET)
        vonage_client = Vonage(auth=auth)
        print("✅ Vonage SMS ready")
    else:
        print("⚠️ Vonage credentials missing")
except Exception as e:
    print(f"⚠️ Vonage SMS not available (app will still work): {e}")

@app.get("/")
def root():
    return {"status": "COYOTE is alive", "integrations": Config.validate()}

@app.get("/health")
def health():
    return {"status": "healthy", "integrations": Config.validate()}

@app.api_route("/webhook/inbound", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    """Handle incoming SMS from Vonage"""
    try:
        # Parse GET params, form data, or JSON
        if request.method == "GET":
            data = dict(request.query_params)
        elif "application/json" in request.headers.get("content-type", ""):
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        # Extract message details
        from_number = data.get("msisdn") or data.get("from")
        text = data.get("text") or data.get("message", "")

        if not text:
            return PlainTextResponse("OK")

        print(f"📱 Incoming from {from_number}: {text}")

        # Process with Claude + tools
        response = handle_message(text)

        print(f"🐺 Response: {response}")

        # Send SMS reply
        print(f"🔍 Debug: vonage_client={vonage_client is not None}, phone={Config.VONAGE_PHONE_NUMBER}")
        if vonage_client and Config.VONAGE_PHONE_NUMBER:
            try:
                result = vonage_client.sms.send({
                    "from_": Config.VONAGE_PHONE_NUMBER,
                    "to": from_number,
                    "text": response[:160]  # SMS char limit
                })
                print(f"✅ SMS sent to {from_number}")
                print(f"📊 Result: {result}")
            except Exception as e:
                print(f"❌ SMS send error: {e}")
        else:
            print(f"⚠️ SMS sending disabled - Vonage not initialized")

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
