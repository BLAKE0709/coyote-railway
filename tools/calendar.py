from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import os

def get_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        return None

    creds_data = json.loads(creds_json)
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret")
    )
    return build('calendar', 'v3', credentials=creds)

def get_today() -> dict:
    """Get today's calendar events"""
    service = get_service()
    if not service:
        return {"error": "Calendar not configured"}

    try:
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
        end = now.replace(hour=23, minute=59, second=59).isoformat() + 'Z'

        results = service.events().list(
            calendarId='primary', timeMin=start, timeMax=end,
            singleEvents=True, orderBy='startTime'
        ).execute()

        events = []
        for event in results.get('items', []):
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            events.append({
                "title": event.get('summary', 'No title'),
                "start": start_time,
                "location": event.get('location', '')[:30]
            })

        return {"date": now.strftime("%Y-%m-%d"), "count": len(events), "events": events}
    except Exception as e:
        return {"error": str(e)}

def get_upcoming(days: int = 7) -> dict:
    """Get upcoming events for next N days"""
    service = get_service()
    if not service:
        return {"error": "Calendar not configured"}

    try:
        now = datetime.utcnow()
        end = now + timedelta(days=days)

        results = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=end.isoformat() + 'Z',
            singleEvents=True, orderBy='startTime', maxResults=20
        ).execute()

        events = []
        for event in results.get('items', []):
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            events.append({
                "title": event.get('summary', 'No title'),
                "start": start_time
            })

        return {"days": days, "count": len(events), "events": events}
    except Exception as e:
        return {"error": str(e)}

def get_next() -> dict:
    """Get the next upcoming event"""
    service = get_service()
    if not service:
        return {"error": "Calendar not configured"}

    try:
        now = datetime.utcnow().isoformat() + 'Z'
        results = service.events().list(
            calendarId='primary', timeMin=now,
            singleEvents=True, orderBy='startTime', maxResults=1
        ).execute()

        events = results.get('items', [])
        if not events:
            return {"next": None, "message": "No upcoming events"}

        event = events[0]
        return {
            "title": event.get('summary', 'No title'),
            "start": event['start'].get('dateTime', event['start'].get('date')),
            "location": event.get('location', '')
        }
    except Exception as e:
        return {"error": str(e)}

def create_event(title: str, start: str, end: str, description: str = "") -> dict:
    """Create a calendar event"""
    service = get_service()
    if not service:
        return {"error": "Calendar not configured"}

    try:
        event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start, 'timeZone': 'America/Chicago'},
            'end': {'dateTime': end, 'timeZone': 'America/Chicago'}
        }

        result = service.events().insert(calendarId='primary', body=event).execute()
        return {"created": True, "id": result['id'], "title": title}
    except Exception as e:
        return {"error": str(e)}
