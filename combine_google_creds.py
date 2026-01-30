#!/usr/bin/env python3
"""
COYOTE Google Credentials Combiner for Railway
Automatically finds and combines Google OAuth credentials into a single JSON
"""

import json
import sys
from pathlib import Path

def find_files():
    """Find Google credential files automatically"""
    home = Path.home()

    cred_locations = [
        home / "coyote" / "config" / "google-credentials.json",
        home / "coyote-railway" / "config" / "google-credentials.json",
        home / "coyote-railway" / "google-credentials.json",
        home / "atlas" / "config" / "google-credentials.json",
        home / "atlas" / "google-credentials.json",
        home / "google-credentials.json",
        home / ".config" / "google-credentials.json",
    ]

    token_locations = [
        home / "coyote" / "config" / "google-token.json",
        home / "coyote" / "config" / "token.json",
        home / "coyote-railway" / "config" / "google-token.json",
        home / "coyote-railway" / "google-token.json",
        home / "coyote-railway" / "token.json",
        home / "atlas" / "config" / "google-token.json",
        home / "atlas" / "google-token.json",
        home / "atlas" / "token.json",
        home / "google-token.json",
        home / "token.json",
        home / ".config" / "google-token.json",
    ]

    creds_path = None
    token_path = None

    print("🔍 Searching for Google credentials...")
    for p in cred_locations:
        if p.exists():
            creds_path = p
            print(f"✅ Found credentials: {p}")
            break

    print("🔍 Searching for Google token...")
    for p in token_locations:
        if p.exists():
            token_path = p
            print(f"✅ Found token: {p}")
            break

    return creds_path, token_path

def combine(creds_path, token_path):
    """Combine into single JSON for Railway"""
    with open(creds_path) as f:
        creds = json.load(f)

    with open(token_path) as f:
        token = json.load(f)

    # Get client info from either format
    client_info = creds.get("installed") or creds.get("web") or {}

    combined = {
        "token": token.get("access_token") or token.get("token"),
        "refresh_token": token.get("refresh_token"),
        "client_id": client_info.get("client_id"),
        "client_secret": client_info.get("client_secret")
    }

    # Validate
    missing = [k for k, v in combined.items() if not v]
    if missing:
        print(f"⚠️  Warning: Missing fields: {missing}")
    else:
        print("✅ All required fields present")

    return json.dumps(combined)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🐺 COYOTE GOOGLE CREDENTIALS COMBINER")
    print("="*60 + "\n")

    # Check for command line arguments
    if len(sys.argv) >= 3:
        creds_path = Path(sys.argv[1])
        token_path = Path(sys.argv[2])
        print(f"📁 Using provided paths:")
        print(f"   Credentials: {creds_path}")
        print(f"   Token: {token_path}")
    else:
        creds_path, token_path = find_files()

    if not creds_path or not creds_path.exists():
        print("\n❌ Could not find google-credentials.json")
        print("\nOptions:")
        print("1. Specify paths: python combine_google_creds.py <credentials.json> <token.json>")
        print("2. Create credentials at: https://console.cloud.google.com")
        print("   - Create new project")
        print("   - Enable Gmail, Calendar, Drive APIs")
        print("   - Create OAuth 2.0 credentials (Desktop app)")
        print("   - Download credentials.json")
        print("   - Run OAuth flow to get token.json")
        sys.exit(1)

    if not token_path or not token_path.exists():
        print("\n❌ Could not find google-token.json")
        print("\nYou need to run the OAuth flow first to get token.json")
        print("This requires running a Google API client with the credentials.json file")
        sys.exit(1)

    result = combine(creds_path, token_path)

    print("\n" + "="*60)
    print("📋 COPY THIS ENTIRE LINE FOR RAILWAY:")
    print("="*60)
    print(result)
    print("="*60)

    # Save to file for easy access
    output_path = Path.home() / "coyote-railway" / "GOOGLE_CREDENTIALS_JSON.txt"
    with open(output_path, "w") as f:
        f.write(result)
    print(f"\n✅ Also saved to: {output_path}")

    # Create Railway instructions
    instructions = f"""
================================================================================
🚀 RAILWAY DEPLOYMENT INSTRUCTIONS
================================================================================

1. Go to: https://railway.app/dashboard
2. Click on your COYOTE project
3. Click on the service (coyote-railway)
4. Go to "Variables" tab
5. Add or update this variable:

   Name: GOOGLE_CREDENTIALS_JSON
   Value: {result}

6. Railway will auto-redeploy (takes ~1-2 minutes)

7. Test by texting +1 949-817-7088:
   - "status" - Should respond
   - "emails" - Should show your inbox
   - "schedule" - Should show calendar

================================================================================
TROUBLESHOOTING
================================================================================

If Gmail/Calendar don't work:
- Check Railway logs for "Gmail not configured" errors
- Verify the GOOGLE_CREDENTIALS_JSON variable was set correctly
- Ensure token hasn't expired (may need to regenerate)
- Verify APIs are enabled in Google Cloud Console

If you see "token expired":
- Regenerate token.json by running OAuth flow again
- Re-run this script
- Update Railway variable

================================================================================
"""

    instructions_path = Path.home() / "coyote-railway" / "RAILWAY_GOOGLE_SETUP.txt"
    with open(instructions_path, "w") as f:
        f.write(instructions)
    print(f"✅ Instructions saved to: {instructions_path}")

    print("\n🎯 NEXT: Follow the instructions above to add to Railway")
    print("📋 Or see: ~/coyote-railway/RAILWAY_GOOGLE_SETUP.txt")
