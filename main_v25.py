"""
COYOTE V2.5 - FastAPI Integration

Combines existing SMS/tool functionality with V2.5 governance pipeline.
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os
import sys

# Add parent directory to path for coyote_v2 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config as LegacyConfig
from claude_handler import handle_message as legacy_handle_message

# V2.5 imports
from coyote_v2 import (
    CoyoteAgent, Config as V25Config, TriggerType, ActionType,
    AuditTrail, AutonomyEngine, ModelRouter, SkillsManager,
    MemoryManager, OutcomeTracker
)

app = FastAPI(title="COYOTE V2.5 - AI Chief of Staff")

# =============================================================================
# INITIALIZATION
# =============================================================================

# Workspace path - use persistent storage on Railway
WORKSPACE = Path(os.getenv("COYOTE_WORKSPACE", "./workspace"))
WORKSPACE.mkdir(exist_ok=True)

# Initialize V2.5 config
v25_config = V25Config(
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
    twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER", ""),
    blake_phone_number=os.getenv("BLAKE_PHONE_NUMBER", ""),
    workspace_path=WORKSPACE
)

# Initialize V2.5 agent
agent = CoyoteAgent(v25_config)

# Initialize Twilio for SMS replies
twilio_client = None
try:
    from twilio.rest import Client
    if LegacyConfig.TWILIO_ACCOUNT_SID and LegacyConfig.TWILIO_AUTH_TOKEN:
        twilio_client = Client(LegacyConfig.TWILIO_ACCOUNT_SID, LegacyConfig.TWILIO_AUTH_TOKEN)
        print("[OK] Twilio SMS ready")
except Exception as e:
    print(f"[--] Twilio not available: {e}")

print(f"[OK] COYOTE V2.5 initialized")
print(f"[OK] Workspace: {WORKSPACE}")
print(f"[OK] Integrations: {v25_config.validate()}")


# =============================================================================
# REQUEST MODELS
# =============================================================================

class ProcessRequest(BaseModel):
    message: str
    agent_id: Optional[str] = "coyote"
    force_model: Optional[str] = None


class ApprovalRequest(BaseModel):
    request_id: str
    approved: bool
    reason: Optional[str] = ""


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.get("/")
def root():
    return {
        "status": "COYOTE V2.5 is alive",
        "version": "2.5.0",
        "integrations": v25_config.validate()
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "2.5.0",
        "integrations": v25_config.validate()
    }


@app.get("/status")
def status():
    """Full V2.5 status"""
    return agent.get_status()


# =============================================================================
# SMS WEBHOOK (Legacy + V2.5 Audit)
# =============================================================================

@app.api_route("/webhook/inbound", methods=["GET", "POST"])
async def inbound_sms(request: Request):
    """Handle incoming SMS from Twilio - now with V2.5 audit"""
    try:
        # Parse request
        if request.method == "GET":
            data = dict(request.query_params)
        elif "application/json" in request.headers.get("content-type", ""):
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        from_number = data.get("From") or data.get("msisdn") or data.get("from")
        text = data.get("Body") or data.get("text") or data.get("message", "")

        if not text:
            return PlainTextResponse("OK")

        print(f"[SMS] From {from_number}: {text}")

        # Process through V2.5 pipeline for audit/governance
        result = agent.process(
            text,
            trigger_type=TriggerType.WEBHOOK,
            trigger_source=f"sms:{from_number}",
            requesting_agent="coyote"
        )

        # Use legacy handler for actual response (has tools)
        response = legacy_handle_message(text)

        print(f"[COYOTE] {response}")
        print(f"[AUDIT] {result.audit_id} | Model: {result.model_used} | Cost: ${result.cost_usd:.4f}")

        # Send SMS reply
        if twilio_client and LegacyConfig.TWILIO_PHONE_NUMBER:
            try:
                twilio_client.messages.create(
                    body=response[:1600],
                    from_=LegacyConfig.TWILIO_PHONE_NUMBER,
                    to=from_number
                )
                print(f"[OK] SMS sent to {from_number}")
            except Exception as e:
                print(f"[ERR] SMS send: {e}")

        return PlainTextResponse("OK")

    except Exception as e:
        print(f"[ERR] Webhook: {e}")
        return PlainTextResponse("OK")


@app.post("/webhook/status")
async def status_webhook(request: Request):
    """Handle delivery receipts"""
    return PlainTextResponse("OK")


# =============================================================================
# SMS ENDPOINT (TwiML Response)
# =============================================================================

@app.post("/sms")
async def sms_webhook(
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    """
    Handle incoming SMS from Twilio with TwiML response.

    - Receives Form data (Body, From)
    - Processes through COYOTE agent
    - Returns TwiML XML response
    """
    try:
        if not Body:
            return Response(
                content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
                media_type="application/xml"
            )

        print(f"[SMS] From {From}: {Body}")

        # Process through V2.5 pipeline for audit/governance
        result = agent.process(
            Body,
            trigger_type=TriggerType.WEBHOOK,
            trigger_source=f"sms:{From}",
            requesting_agent="coyote"
        )

        # Use legacy handler for actual response (has tools)
        response_text = legacy_handle_message(Body)

        print(f"[COYOTE] {response_text}")
        print(f"[AUDIT] {result.audit_id} | Model: {result.model_used} | Cost: ${result.cost_usd:.4f}")

        # Truncate response if too long (SMS limit ~1600 chars)
        if len(response_text) > 1600:
            response_text = response_text[:1597] + "..."

        # Escape XML special characters
        response_text = (
            response_text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        # Return TwiML response
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>'''

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        print(f"[ERR] SMS endpoint: {e}")
        error_twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>COYOTE encountered an error. Please try again.</Message>
</Response>'''
        return Response(content=error_twiml, media_type="application/xml")


# =============================================================================
# V2.5 PROCESS ENDPOINT
# =============================================================================

@app.post("/process")
async def process_message(request: ProcessRequest):
    """Process message through full V2.5 pipeline"""
    result = agent.process(
        request.message,
        trigger_type=TriggerType.WEBHOOK,
        trigger_source="api",
        requesting_agent=request.agent_id,
        force_model=request.force_model
    )

    return {
        "success": result.success,
        "audit_id": result.audit_id,
        "decision": result.decision,
        "action": result.action_taken,
        "autonomy_level": result.autonomy_level.value,
        "model": result.model_used,
        "cost_usd": result.cost_usd,
        "skills": result.skills_used,
        "error": result.error
    }


# =============================================================================
# AUDIT ENDPOINTS
# =============================================================================

@app.get("/audit")
async def get_audit(days: int = 7, agent_id: Optional[str] = None, limit: int = 50):
    """Get audit entries"""
    entries = agent.audit.query(
        agent_id=agent_id,
        limit=limit
    )
    return {
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    }


@app.get("/audit/stats")
async def get_audit_stats(days: int = 7):
    """Get audit statistics"""
    return agent.audit.get_stats(days)


@app.get("/audit/{audit_id}")
async def get_audit_entry(audit_id: str):
    """Get specific audit entry"""
    entries = agent.audit.query(limit=1000)
    for entry in entries:
        if entry.id == audit_id or entry.id.startswith(audit_id):
            return entry.to_dict()
    return {"error": "Not found"}


# =============================================================================
# AUTONOMY ENDPOINTS
# =============================================================================

@app.get("/approvals")
async def get_pending_approvals():
    """Get pending approval requests"""
    pending = agent.autonomy.get_pending_approvals()
    return {"count": len(pending), "pending": pending}


@app.post("/approvals/{request_id}")
async def handle_approval(request_id: str, request: ApprovalRequest):
    """Approve or reject a pending request"""
    if request.approved:
        success = agent.autonomy.approve_request(request_id)
        return {"success": success, "action": "approved"}
    else:
        success = agent.autonomy.reject_request(request_id, reason=request.reason)
        return {"success": success, "action": "rejected"}


# =============================================================================
# COSTS ENDPOINTS
# =============================================================================

@app.get("/costs")
async def get_costs(days: int = 7):
    """Get cost summary"""
    return agent.router.get_cost_summary(days)


@app.get("/costs/today")
async def get_today_costs():
    """Get today's costs"""
    return agent.router.get_today_status()


@app.get("/costs/agent/{agent_id}")
async def get_agent_costs(agent_id: str):
    """Get costs for specific agent"""
    return agent.router.get_agent_budget_status(agent_id)


# =============================================================================
# SKILLS ENDPOINTS
# =============================================================================

@app.get("/skills")
async def list_skills():
    """List all skills"""
    return agent.skills.list_skills()


@app.get("/skills/detect")
async def detect_skills(context: str):
    """Detect relevant skills for context"""
    skill_ids = agent.skills.detect_relevant_skills(context)
    return {"context": context, "skills": skill_ids}


# =============================================================================
# OUTCOMES ENDPOINTS
# =============================================================================

@app.get("/outcomes")
async def get_outcomes_report(agent_id: Optional[str] = None, days: int = 30):
    """Get effectiveness report"""
    return agent.outcomes.get_effectiveness_report(agent_id, days)


@app.get("/outcomes/pending")
async def get_pending_outcomes():
    """Get actions awaiting outcome tracking"""
    return {"pending": agent.audit.get_pending_outcomes()}


# =============================================================================
# MEMORY ENDPOINTS
# =============================================================================

@app.get("/memory/search")
async def search_memory(query: str, limit: int = 10):
    """Search memories"""
    results = agent.memory.search(query, limit=limit)
    return {"count": len(results), "memories": [m.to_dict() for m in results]}


@app.post("/memory")
async def add_memory(content: str, category: str = "general", importance: int = 5):
    """Add a memory"""
    mem = agent.memory.add(content=content, category=category, importance=importance)
    return {"id": mem.id, "content": mem.content}


# =============================================================================
# HEARTBEAT
# =============================================================================

@app.post("/heartbeat")
async def run_heartbeat():
    """Run heartbeat check"""
    result = agent.run_heartbeat()
    return {
        "success": result.success,
        "audit_id": result.audit_id,
        "decision": result.decision
    }


# =============================================================================
# LEGACY TEST ENDPOINTS
# =============================================================================

@app.post("/test")
async def test_message(request: Request):
    """Test endpoint - uses legacy handler"""
    try:
        data = await request.json()
        message = data.get("message", "status")
        response = legacy_handle_message(message)
        return {"input": message, "response": response}
    except Exception as e:
        return {"error": str(e)}


@app.get("/test/{message}")
async def test_get(message: str):
    """GET test endpoint"""
    response = legacy_handle_message(message)
    return {"input": message, "response": response}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
