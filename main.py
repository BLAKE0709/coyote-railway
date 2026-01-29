from fastapi import FastAPI, Request
import httpx
import os

app = FastAPI()

@app.get("/")
def health():
    return {"status": "COYOTE online 🐺"}

@app.post("/webhook/inbound")
async def inbound_sms(request: Request):
    data = await request.form()
    message = data.get("text", "")
    sender = data.get("msisdn", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "content-type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 300,
                "system": "You are COYOTE 🐺, Blake's AI chief of staff. Be concise - SMS limits. Sign with 🐺",
                "messages": [{"role": "user", "content": message}]
            }
        )
        reply = response.json()["content"][0]["text"]

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://rest.nexmo.com/sms/json",
            data={
                "api_key": os.environ["VONAGE_API_KEY"],
                "api_secret": os.environ["VONAGE_API_SECRET"],
                "from": os.environ["VONAGE_FROM_NUMBER"],
                "to": sender,
                "text": reply[:160]
            }
        )
    return {"status": "ok"}
