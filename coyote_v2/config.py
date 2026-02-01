"""
COYOTE V2.5 - Configuration Management

Centralized configuration for all COYOTE services.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Configuration for COYOTE services"""

    # Anthropic
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    # Twilio SMS
    twilio_account_sid: str = field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", ""))
    twilio_phone_number: str = field(default_factory=lambda: os.getenv("TWILIO_PHONE_NUMBER", ""))
    blake_phone_number: str = field(default_factory=lambda: os.getenv("BLAKE_PHONE_NUMBER", ""))

    # Google credentials
    google_credentials_json: str = field(default_factory=lambda: os.getenv("GOOGLE_CREDENTIALS_JSON", ""))

    # Supabase
    supabase_url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    supabase_key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))

    # Workspace
    workspace_path: Path = field(default_factory=lambda: Path(os.getenv("COYOTE_WORKSPACE", "./workspace")))

    # Budget
    daily_budget_usd: float = field(default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "50")))

    def __post_init__(self):
        # Ensure workspace exists
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def get_google_creds(self) -> Optional[dict]:
        """Parse Google credentials from JSON string"""
        if self.google_credentials_json:
            try:
                return json.loads(self.google_credentials_json)
            except json.JSONDecodeError:
                return None
        return None

    def validate(self) -> dict:
        """Validate configuration, return status of each service"""
        return {
            "anthropic": bool(self.anthropic_api_key),
            "twilio": bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_phone_number),
            "google": bool(self.google_credentials_json),
            "supabase": bool(self.supabase_url and self.supabase_key),
            "workspace": self.workspace_path.exists()
        }

    def is_valid(self) -> bool:
        """Check if minimum required config is present"""
        return bool(self.anthropic_api_key)

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables"""
        return cls()

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        """Create config from a JSON file"""
        data = json.loads(path.read_text())
        return cls(
            anthropic_api_key=data.get("anthropic_api_key", ""),
            twilio_account_sid=data.get("twilio_account_sid", ""),
            twilio_auth_token=data.get("twilio_auth_token", ""),
            twilio_phone_number=data.get("twilio_phone_number", ""),
            blake_phone_number=data.get("blake_phone_number", ""),
            google_credentials_json=data.get("google_credentials_json", ""),
            supabase_url=data.get("supabase_url", ""),
            supabase_key=data.get("supabase_key", ""),
            workspace_path=Path(data.get("workspace_path", "./workspace")),
            daily_budget_usd=float(data.get("daily_budget_usd", 50))
        )

    def to_dict(self) -> dict:
        """Export config as dict (without secrets)"""
        return {
            "anthropic": "***" if self.anthropic_api_key else None,
            "twilio": "***" if self.twilio_account_sid else None,
            "twilio_phone": self.twilio_phone_number,
            "blake_phone": self.blake_phone_number,
            "google": "***" if self.google_credentials_json else None,
            "supabase_url": self.supabase_url,
            "workspace_path": str(self.workspace_path),
            "daily_budget_usd": self.daily_budget_usd
        }
