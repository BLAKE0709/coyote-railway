import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Anthropic
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Vonage SMS
    VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
    VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")
    VONAGE_PHONE_NUMBER = os.getenv("VONAGE_PHONE_NUMBER") or "19498177088"  # Fallback

    # Google - stored as single JSON string in Railway
    GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

    # Supabase (for revenue)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Swarm API (if deployed separately)
    SWARM_API_URL = os.getenv("SWARM_API_URL", "http://localhost:8000")

    @classmethod
    def get_google_creds(cls) -> dict:
        if cls.GOOGLE_CREDENTIALS_JSON:
            return json.loads(cls.GOOGLE_CREDENTIALS_JSON)
        return None

    @classmethod
    def validate(cls) -> dict:
        return {
            "anthropic": bool(cls.ANTHROPIC_API_KEY),
            "vonage": bool(cls.VONAGE_API_KEY and cls.VONAGE_API_SECRET),
            "google": bool(cls.GOOGLE_CREDENTIALS_JSON),
            "supabase": bool(cls.SUPABASE_URL and cls.SUPABASE_KEY)
        }
