"""
COYOTE V2.5 - Unified Audit Trail

Every action by any agent is permanently logged with full context.
Single source of truth for trust, debugging, compliance, and learning.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List
from pathlib import Path
from enum import Enum
import json
import uuid


class TriggerType(Enum):
    HEARTBEAT = "heartbeat"
    WEBHOOK = "webhook"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    AGENT_REQUEST = "agent_request"
    ESCALATION = "escalation"


class ActionType(Enum):
    ALERT = "alert"
    EMAIL = "email"
    API_CALL = "api_call"
    CODE_EXECUTION = "code_execution"
    CLAUDE_CODE = "claude_code"
    LOG_ONLY = "log_only"
    DELEGATE = "delegate"
    APPROVAL_REQUEST = "approval_request"


class ActionResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"


class AutonomyLevel(Enum):
    AUTONOMOUS = "autonomous"
    NOTIFY = "notify"
    APPROVAL_REQUIRED = "approval_required"


class OutcomeStatus(Enum):
    PENDING = "pending"
    ACTED_ON = "acted_on"
    IGNORED = "ignored"
    DELAYED = "delayed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass
class AuditEntry:
    """Complete record of an agent action"""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Source
    agent_id: str = "coyote"
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_source: str = ""
    parent_audit_id: Optional[str] = None

    # Context
    context_summary: str = ""
    memory_retrieved: List[str] = field(default_factory=list)
    skills_loaded: List[str] = field(default_factory=list)
    input_data: dict = field(default_factory=dict)

    # Decision
    decision: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    autonomy_level: AutonomyLevel = AutonomyLevel.NOTIFY
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0

    # Action
    action_type: ActionType = ActionType.LOG_ONLY
    action_details: dict = field(default_factory=dict)
    action_result: ActionResult = ActionResult.PENDING
    error_message: Optional[str] = None
    delegated_to: Optional[str] = None

    # Outcome
    outcome_tracked: bool = False
    outcome_status: Optional[OutcomeStatus] = None
    outcome_timestamp: Optional[datetime] = None
    outcome_value_usd: Optional[float] = None
    outcome_notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "trigger_type": self.trigger_type.value,
            "trigger_source": self.trigger_source,
            "parent_audit_id": self.parent_audit_id,
            "context_summary": self.context_summary,
            "memory_retrieved": self.memory_retrieved,
            "skills_loaded": self.skills_loaded,
            "input_data": self.input_data,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "autonomy_level": self.autonomy_level.value,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "action_type": self.action_type.value,
            "action_details": self.action_details,
            "action_result": self.action_result.value,
            "error_message": self.error_message,
            "delegated_to": self.delegated_to,
            "outcome_tracked": self.outcome_tracked,
            "outcome_status": self.outcome_status.value if self.outcome_status else None,
            "outcome_timestamp": self.outcome_timestamp.isoformat() if self.outcome_timestamp else None,
            "outcome_value_usd": self.outcome_value_usd,
            "outcome_notes": self.outcome_notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        entry = cls()
        entry.id = data["id"]
        entry.timestamp = datetime.fromisoformat(data["timestamp"])
        entry.agent_id = data["agent_id"]
        entry.trigger_type = TriggerType(data["trigger_type"])
        entry.trigger_source = data["trigger_source"]
        entry.parent_audit_id = data.get("parent_audit_id")
        entry.context_summary = data["context_summary"]
        entry.memory_retrieved = data.get("memory_retrieved", [])
        entry.skills_loaded = data.get("skills_loaded", [])
        entry.input_data = data.get("input_data", {})
        entry.decision = data["decision"]
        entry.reasoning = data.get("reasoning", "")
        entry.confidence = data.get("confidence", 0.0)
        entry.autonomy_level = AutonomyLevel(data["autonomy_level"])
        entry.model_used = data.get("model_used", "")
        entry.tokens_used = data.get("tokens_used", 0)
        entry.cost_usd = data.get("cost_usd", 0.0)
        entry.action_type = ActionType(data["action_type"])
        entry.action_details = data.get("action_details", {})
        entry.action_result = ActionResult(data["action_result"])
        entry.error_message = data.get("error_message")
        entry.delegated_to = data.get("delegated_to")
        entry.outcome_tracked = data.get("outcome_tracked", False)
        entry.outcome_status = OutcomeStatus(data["outcome_status"]) if data.get("outcome_status") else None
        entry.outcome_timestamp = datetime.fromisoformat(data["outcome_timestamp"]) if data.get("outcome_timestamp") else None
        entry.outcome_value_usd = data.get("outcome_value_usd")
        entry.outcome_notes = data.get("outcome_notes")
        return entry


class AuditTrail:
    """Unified audit trail for all agent actions"""

    def __init__(self, workspace_path: Path):
        self.audit_dir = workspace_path / "audit"
        self.audit_dir.mkdir(exist_ok=True)
        self.index_path = self.audit_dir / "index.json"
        self._load_index()

    def _load_index(self):
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text())
        else:
            self.index = {"by_agent": {}, "pending_outcomes": []}

    def _save_index(self):
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def _get_daily_file(self, dt: date) -> Path:
        return self.audit_dir / f"{dt.isoformat()}.jsonl"

    def log_action(self, entry: AuditEntry) -> str:
        """Log an action, return the audit ID"""
        # Use local date for file organization to match query behavior
        daily_file = self._get_daily_file(date.today())
        with open(daily_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        agent = entry.agent_id
        if agent not in self.index["by_agent"]:
            self.index["by_agent"][agent] = {"count": 0, "last_action": None}
        self.index["by_agent"][agent]["count"] += 1
        self.index["by_agent"][agent]["last_action"] = entry.timestamp.isoformat()

        if entry.action_type != ActionType.LOG_ONLY and not entry.outcome_tracked:
            self.index["pending_outcomes"].append({
                "id": entry.id,
                "timestamp": entry.timestamp.isoformat(),
                "agent_id": entry.agent_id,
                "action_type": entry.action_type.value
            })

        self._save_index()
        return entry.id

    def update_outcome(
        self,
        audit_id: str,
        status: OutcomeStatus,
        value_usd: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update an entry with its outcome"""
        for days_back in range(30):
            dt = date.today() - timedelta(days=days_back)
            daily_file = self._get_daily_file(dt)
            if not daily_file.exists():
                continue

            lines = daily_file.read_text().strip().split("\n")
            updated = False
            new_lines = []

            for line in lines:
                if not line:
                    continue
                entry_dict = json.loads(line)
                if entry_dict["id"] == audit_id:
                    entry_dict["outcome_tracked"] = True
                    entry_dict["outcome_status"] = status.value
                    entry_dict["outcome_timestamp"] = datetime.utcnow().isoformat()
                    entry_dict["outcome_value_usd"] = value_usd
                    entry_dict["outcome_notes"] = notes
                    updated = True
                new_lines.append(json.dumps(entry_dict))

            if updated:
                daily_file.write_text("\n".join(new_lines) + "\n")
                self.index["pending_outcomes"] = [
                    p for p in self.index["pending_outcomes"]
                    if p["id"] != audit_id
                ]
                self._save_index()
                return True

        return False

    def query(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        agent_id: Optional[str] = None,
        trigger_type: Optional[TriggerType] = None,
        action_type: Optional[ActionType] = None,
        outcome_status: Optional[OutcomeStatus] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Query audit entries with filters"""
        start = start_date or (date.today() - timedelta(days=7))
        end = end_date or date.today()

        results = []
        current = start

        while current <= end and len(results) < limit:
            daily_file = self._get_daily_file(current)
            if daily_file.exists():
                for line in daily_file.read_text().strip().split("\n"):
                    if not line:
                        continue
                    entry = AuditEntry.from_dict(json.loads(line))

                    if agent_id and entry.agent_id != agent_id:
                        continue
                    if trigger_type and entry.trigger_type != trigger_type:
                        continue
                    if action_type and entry.action_type != action_type:
                        continue
                    if outcome_status and entry.outcome_status != outcome_status:
                        continue

                    results.append(entry)
                    if len(results) >= limit:
                        break

            current += timedelta(days=1)

        return results

    def get_stats(self, days: int = 7) -> dict:
        """Get summary statistics"""
        entries = self.query(
            start_date=date.today() - timedelta(days=days),
            limit=10000
        )

        stats = {
            "period_days": days,
            "total_actions": len(entries),
            "by_agent": {},
            "by_action_type": {},
            "by_outcome": {},
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "success_rate": 0.0,
            "outcome_rate": 0.0
        }

        successes = 0
        outcomes_tracked = 0

        for entry in entries:
            agent = entry.agent_id
            if agent not in stats["by_agent"]:
                stats["by_agent"][agent] = 0
            stats["by_agent"][agent] += 1

            action = entry.action_type.value
            if action not in stats["by_action_type"]:
                stats["by_action_type"][action] = 0
            stats["by_action_type"][action] += 1

            if entry.outcome_status:
                outcome = entry.outcome_status.value
                if outcome not in stats["by_outcome"]:
                    stats["by_outcome"][outcome] = 0
                stats["by_outcome"][outcome] += 1
                outcomes_tracked += 1

            stats["total_cost_usd"] += entry.cost_usd
            stats["total_tokens"] += entry.tokens_used

            if entry.action_result == ActionResult.SUCCESS:
                successes += 1

        if entries:
            stats["success_rate"] = successes / len(entries)
            stats["outcome_rate"] = outcomes_tracked / len(entries)

        return stats

    def get_pending_outcomes(self) -> List[dict]:
        """Get actions needing outcome tracking"""
        return self.index.get("pending_outcomes", [])
