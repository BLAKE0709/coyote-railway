from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
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
    return build('drive', 'v3', credentials=creds)

def search(query: str, max_results: int = 10) -> dict:
    """Search Google Drive for files"""
    service = get_service()
    if not service:
        return {"error": "Drive not configured"}

    try:
        # Search in file names and content
        results = service.files().list(
            q=f"name contains '{query}' or fullText contains '{query}'",
            spaces='drive',
            fields='files(id, name, mimeType, modifiedTime, webViewLink)',
            pageSize=max_results
        ).execute()

        files = []
        for f in results.get('files', []):
            files.append({
                "id": f['id'],
                "name": f['name'],
                "type": f['mimeType'].split('.')[-1] if '.' in f['mimeType'] else f['mimeType'],
                "modified": f.get('modifiedTime', '')[:10],
                "link": f.get('webViewLink', '')
            })

        return {"count": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}

def get_recent(count: int = 10) -> dict:
    """Get recently modified files"""
    service = get_service()
    if not service:
        return {"error": "Drive not configured"}

    try:
        results = service.files().list(
            orderBy='modifiedTime desc',
            fields='files(id, name, mimeType, modifiedTime)',
            pageSize=count
        ).execute()

        files = []
        for f in results.get('files', []):
            files.append({
                "name": f['name'],
                "modified": f.get('modifiedTime', '')[:10]
            })

        return {"count": len(files), "files": files}
    except Exception as e:
        return {"error": str(e)}
