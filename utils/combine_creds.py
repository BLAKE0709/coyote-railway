"""
Run this to combine Google credentials into a single JSON for Railway.

Usage:
  python utils/combine_creds.py <credentials_file> <token_file>

Example:
  python utils/combine_creds.py ~/coyote/config/google-credentials.json ~/coyote/config/google-token.json
"""

import json
import sys

def combine(creds_path: str, token_path: str) -> str:
    with open(creds_path) as f:
        creds = json.load(f)

    with open(token_path) as f:
        token = json.load(f)

    # Get client info
    client_info = creds.get("installed") or creds.get("web") or {}

    combined = {
        "token": token.get("access_token") or token.get("token"),
        "refresh_token": token.get("refresh_token"),
        "client_id": client_info.get("client_id"),
        "client_secret": client_info.get("client_secret")
    }

    return json.dumps(combined)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Try to find files automatically
        import os
        from pathlib import Path

        home = Path.home()
        possible_creds = [
            home / "coyote" / "config" / "google-credentials.json",
            home / "atlas" / "config" / "google-credentials.json",
            home / "coyote-railway" / "google-credentials.json",
        ]
        possible_tokens = [
            home / "coyote" / "config" / "google-token.json",
            home / "atlas" / "config" / "google-token.json",
            home / "coyote-railway" / "google-token.json",
        ]

        creds_path = None
        token_path = None

        for p in possible_creds:
            if p.exists():
                creds_path = str(p)
                print(f"Found credentials: {p}")
                break

        for p in possible_tokens:
            if p.exists():
                token_path = str(p)
                print(f"Found token: {p}")
                break

        if not creds_path or not token_path:
            print("Could not find Google credential files automatically.")
            print("Usage: python combine_creds.py <credentials.json> <token.json>")
            sys.exit(1)
    else:
        creds_path = sys.argv[1]
        token_path = sys.argv[2]

    result = combine(creds_path, token_path)

    print("\n" + "="*60)
    print("Add this to Railway as GOOGLE_CREDENTIALS_JSON:")
    print("="*60)
    print(result)
    print("="*60)

    # Also save to file
    with open("GOOGLE_CREDENTIALS_JSON.txt", "w") as f:
        f.write(result)
    print("\nAlso saved to: GOOGLE_CREDENTIALS_JSON.txt")
