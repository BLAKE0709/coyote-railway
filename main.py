from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse, JSONResponse
import vonage
import os
from claude_handler import handle_message
from config import Config

app = FastAPI(title="COYOTE - AI Chief of Staff")

# Vonage client
vonage_client = None
sms = None
if Config.VONAGE_API_KEY and Config.VONAGE_API_SECRET:
    try:
        # Try new Vonage SDK v3+ syntax
        from vonage_sms import SmsClient
        vonage_client = SmsClient(
            api_key=Config.VONAGE_API_KEY,
            api_secret=Config.VONAGE_API_SECRET
        )
        sms = vonage_client
    except (ImportError, AttributeError):
        # Fallback to old syntax (if older version installed)
        import vonage
        vonage_client = vonage.Client(
            key=Config.VONAGE_API_KEY,
            secret=Config.VONAGE_API_SECRET
        )
        sms = vonage.Sms(vonage_client)

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
        if vonage_client and from_number:
            # Truncate to 160 chars for SMS
            sms_response = response[:157] + "..." if len(response) > 160 else response

            sms.send_message({
                "from": Config.VONAGE_PHONE_NUMBER,
                "to": from_number,
                "text": sms_response
            })

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
