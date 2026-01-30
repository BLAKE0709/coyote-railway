from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
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
    return build('gmail', 'v1', credentials=creds)

def search(query: str, max_results: int = 5) -> dict:
    """Search Gmail with query like 'from:john' or 'subject:invoice'"""
    service = get_service()
    if not service:
        return {"error": "Gmail not configured"}

    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages[:max_results]:
            detail = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in detail['payload']['headers']}
            emails.append({
                "id": msg['id'],
                "from": headers.get('From', '')[:50],
                "subject": headers.get('Subject', '')[:50],
                "date": headers.get('Date', '')[:20],
                "snippet": detail.get('snippet', '')[:80]
            })

        return {"count": len(emails), "emails": emails}
    except Exception as e:
        return {"error": str(e)}

def unread_count() -> dict:
    """Get count of unread emails"""
    service = get_service()
    if not service:
        return {"error": "Gmail not configured"}

    try:
        results = service.users().messages().list(
            userId='me', q='is:unread'
        ).execute()
        return {"unread": results.get('resultSizeEstimate', 0)}
    except Exception as e:
        return {"error": str(e)}

def get_recent(count: int = 5) -> dict:
    """Get most recent emails"""
    return search("", count)

def send(to: str, subject: str, body: str) -> dict:
    """Send an email"""
    service = get_service()
    if not service:
        return {"error": "Gmail not configured"}

    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId='me', body={'raw': raw}
        ).execute()

        return {"sent": True, "id": result['id'], "to": to}
    except Exception as e:
        return {"error": str(e)}
