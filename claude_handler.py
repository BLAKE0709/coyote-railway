import anthropic
import json
from tools import gmail, calendar, drive, swarm, revenue

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "gmail_search",
        "description": "Search Gmail. Examples: 'from:john', 'subject:invoice', 'is:unread', 'martin marietta'",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "gmail_unread",
        "description": "Get count of unread emails",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "gmail_recent",
        "description": "Get most recent emails",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 5}
            }
        }
    },
    {
        "name": "gmail_send",
        "description": "Send an email",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "calendar_today",
        "description": "Get today's calendar events",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "calendar_upcoming",
        "description": "Get upcoming events",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 7, "description": "Number of days to look ahead"}
            }
        }
    },
    {
        "name": "calendar_next",
        "description": "Get the next upcoming event",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "calendar_create",
        "description": "Create a calendar event",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start": {"type": "string", "description": "ISO datetime e.g. 2025-01-30T14:00:00"},
                "end": {"type": "string", "description": "ISO datetime"},
                "description": {"type": "string", "default": ""}
            },
            "required": ["title", "start", "end"]
        }
    },
    {
        "name": "drive_search",
        "description": "Search Google Drive for files",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "drive_recent",
        "description": "Get recently modified files",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "swarm_status",
        "description": "Get status of all swarms (Prophet, Hydra, Vulture, Signal)",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "prophet_stats",
        "description": "Get Prophet lead generation statistics",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "revenue_summary",
        "description": "Get revenue summary: today, MTD, MRR, subscriber count",
        "input_schema": {"type": "object", "properties": {}}
    }
]

SYSTEM_PROMPT = """You are COYOTE, Blake's AI Chief of Staff. You communicate via SMS.

Blake is the Founder/CEO of Atlas Industrial, a climate tech company developing thermal symbiosis technology that converts industrial waste heat into power for hyperscaler compute infrastructure. Based in Colleyville, Texas.

He's also building a swarm empire of AI agents (Prophet for permit leads, Hydra for content, Vulture for distress monitoring, Signal for market intelligence).

You have access to:
- Gmail (search, read, send emails)
- Calendar (view today/upcoming, create events)
- Google Drive (search files)
- Swarm systems (status, Prophet stats)
- Revenue tracking (today, MTD, MRR)

CRITICAL SMS RULES:
- Keep responses under 160 characters when possible
- Be extremely concise - every character counts
- Use abbreviations: mtg=meeting, tmrw=tomorrow, w/=with
- No fluff, no pleasantries, just information
- If listing multiple items, use | as separator

You're not a chatbot. You're a chief of staff. Anticipate needs. Take action. Report results."""

def handle_message(user_message: str) -> str:
    """Process SMS message with Claude and tools, return response"""

    messages = [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

    # Handle tool use loop
    while response.stop_reason == "tool_use":
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result)
                })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

    # Extract text response
    for block in response.content:
        if hasattr(block, 'text'):
            return block.text

    return "No response generated"

def execute_tool(name: str, inputs: dict) -> dict:
    """Execute a tool by name"""
    try:
        if name == "gmail_search":
            return gmail.search(inputs.get("query", ""))
        elif name == "gmail_unread":
            return gmail.unread_count()
        elif name == "gmail_recent":
            return gmail.get_recent(inputs.get("count", 5))
        elif name == "gmail_send":
            return gmail.send(inputs["to"], inputs["subject"], inputs["body"])
        elif name == "calendar_today":
            return calendar.get_today()
        elif name == "calendar_upcoming":
            return calendar.get_upcoming(inputs.get("days", 7))
        elif name == "calendar_next":
            return calendar.get_next()
        elif name == "calendar_create":
            return calendar.create_event(
                inputs["title"], inputs["start"], inputs["end"],
                inputs.get("description", "")
            )
        elif name == "drive_search":
            return drive.search(inputs.get("query", ""))
        elif name == "drive_recent":
            return drive.get_recent(inputs.get("count", 10))
        elif name == "swarm_status":
            return swarm.get_status()
        elif name == "prophet_stats":
            return swarm.get_prophet_stats()
        elif name == "revenue_summary":
            return revenue.get_summary()
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}
