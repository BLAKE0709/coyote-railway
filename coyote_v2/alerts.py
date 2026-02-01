"""
COYOTE V2.5 - Alert Service

Send SMS alerts via Twilio. Rate-limited and configurable.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import json

from .config import Config


@dataclass
class AlertRecord:
    """Record of an alert sent"""
    timestamp: datetime
    alert_type: str
    urgency: str
    message: str
    recipient: str
    status: str
    error: Optional[str] = None


class AlertService:
    """Manages alert sending with rate limiting"""

    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self._init_twilio()

        # Rate limiting
        self._recent_alerts: List[datetime] = []
        self.max_alerts_per_hour = 5

        # Alert history
        self.history_path = config.workspace_path / "alert_history.jsonl"

    def _init_twilio(self):
        """Initialize Twilio client if credentials available"""
        if self.config.twilio_account_sid and self.config.twilio_auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(
                    self.config.twilio_account_sid,
                    self.config.twilio_auth_token
                )
            except ImportError:
                print("Twilio library not installed. SMS disabled.")
            except Exception as e:
                print(f"Twilio init failed: {e}")

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limit"""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)

        # Clean old entries
        self._recent_alerts = [t for t in self._recent_alerts if t > cutoff]

        return len(self._recent_alerts) < self.max_alerts_per_hour

    def _record_alert(self, record: AlertRecord):
        """Record an alert to history"""
        with open(self.history_path, "a") as f:
            f.write(json.dumps({
                "timestamp": record.timestamp.isoformat(),
                "alert_type": record.alert_type,
                "urgency": record.urgency,
                "message": record.message,
                "recipient": record.recipient,
                "status": record.status,
                "error": record.error
            }) + "\n")

    def send_sms(
        self,
        message: str,
        urgency: str = "normal",
        recipient: Optional[str] = None,
        bypass_rate_limit: bool = False
    ) -> bool:
        """
        Send an SMS alert.

        Args:
            message: The message to send
            urgency: "low", "normal", "high", "critical", or "emergency"
            recipient: Phone number (defaults to Blake's number)
            bypass_rate_limit: Skip rate limiting (for emergencies)

        Returns:
            True if sent successfully
        """
        # Determine recipient
        to_number = recipient or self.config.blake_phone_number
        if not to_number:
            print("No recipient phone number configured")
            return False

        # Check rate limit
        if not bypass_rate_limit and not self._check_rate_limit():
            print(f"Rate limit exceeded ({self.max_alerts_per_hour}/hour)")
            self._record_alert(AlertRecord(
                timestamp=datetime.utcnow(),
                alert_type="sms",
                urgency=urgency,
                message=message[:100],
                recipient=to_number,
                status="rate_limited",
                error="Exceeded hourly rate limit"
            ))
            return False

        # Check Twilio
        if not self.client:
            print("Twilio client not initialized")
            self._record_alert(AlertRecord(
                timestamp=datetime.utcnow(),
                alert_type="sms",
                urgency=urgency,
                message=message[:100],
                recipient=to_number,
                status="failed",
                error="Twilio not configured"
            ))
            return False

        # Send the SMS
        try:
            result = self.client.messages.create(
                body=message[:1600],  # Twilio limit
                from_=self.config.twilio_phone_number,
                to=to_number
            )

            # Track for rate limiting
            self._recent_alerts.append(datetime.utcnow())

            # Record success
            self._record_alert(AlertRecord(
                timestamp=datetime.utcnow(),
                alert_type="sms",
                urgency=urgency,
                message=message[:100],
                recipient=to_number,
                status="sent"
            ))

            print(f"SMS sent to {to_number}: {result.sid}")
            return True

        except Exception as e:
            print(f"SMS send failed: {e}")
            self._record_alert(AlertRecord(
                timestamp=datetime.utcnow(),
                alert_type="sms",
                urgency=urgency,
                message=message[:100],
                recipient=to_number,
                status="failed",
                error=str(e)
            ))
            return False

    def send_alert(
        self,
        message: str,
        urgency: str = "normal",
        alert_type: str = "sms"
    ) -> bool:
        """
        Send an alert using the appropriate method.

        Args:
            message: The message to send
            urgency: "low", "normal", "high", "critical", "emergency"
            alert_type: "sms" or "email" (email not implemented yet)
        """
        if alert_type == "sms":
            # Bypass rate limit for emergencies
            bypass = urgency in ["critical", "emergency"]
            return self.send_sms(message, urgency, bypass_rate_limit=bypass)
        else:
            # Email not implemented yet
            print(f"Alert type '{alert_type}' not implemented")
            return False

    def get_recent_alerts(self, hours: int = 24) -> List[dict]:
        """Get recent alert history"""
        if not self.history_path.exists():
            return []

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        alerts = []

        for line in self.history_path.read_text().strip().split("\n"):
            if not line:
                continue
            alert = json.loads(line)
            if datetime.fromisoformat(alert["timestamp"]) > cutoff:
                alerts.append(alert)

        return alerts

    def get_alert_stats(self, days: int = 7) -> dict:
        """Get alert statistics"""
        if not self.history_path.exists():
            return {"total": 0}

        cutoff = datetime.utcnow() - timedelta(days=days)
        total = 0
        by_status = {}
        by_urgency = {}

        for line in self.history_path.read_text().strip().split("\n"):
            if not line:
                continue
            alert = json.loads(line)
            if datetime.fromisoformat(alert["timestamp"]) < cutoff:
                continue

            total += 1

            status = alert["status"]
            if status not in by_status:
                by_status[status] = 0
            by_status[status] += 1

            urgency = alert["urgency"]
            if urgency not in by_urgency:
                by_urgency[urgency] = 0
            by_urgency[urgency] += 1

        return {
            "period_days": days,
            "total": total,
            "by_status": by_status,
            "by_urgency": by_urgency
        }

    def test_connection(self) -> dict:
        """Test Twilio connection without sending"""
        result = {
            "twilio_configured": bool(self.client),
            "from_number": self.config.twilio_phone_number,
            "to_number": self.config.blake_phone_number,
            "rate_limit_remaining": self.max_alerts_per_hour - len(self._recent_alerts)
        }

        if self.client:
            try:
                # Try to fetch account info to verify credentials
                account = self.client.api.accounts(self.config.twilio_account_sid).fetch()
                result["account_status"] = account.status
                result["connection"] = "ok"
            except Exception as e:
                result["connection"] = "failed"
                result["error"] = str(e)

        return result
