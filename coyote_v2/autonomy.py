"""
COYOTE V2.5 - Autonomy Rules Engine

Unified governance for what any agent can do autonomously vs needs approval.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import yaml
import json

from .audit import AutonomyLevel


@dataclass
class PermissionResult:
    allowed: bool
    level: AutonomyLevel
    reason: str
    conditions_met: List[str]
    conditions_failed: List[str]
    requires_approval_from: Optional[str] = None
    notify_via: Optional[str] = None


class AutonomyEngine:
    """Enforces autonomy rules across all agents"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.rules_path = workspace_path / "AUTONOMY_RULES.yaml"
        self._load_rules()

    def _load_rules(self):
        if self.rules_path.exists():
            self.rules = yaml.safe_load(self.rules_path.read_text())
        else:
            self.rules = self._default_rules()
            self._save_rules()

    def _save_rules(self):
        self.rules_path.write_text(yaml.dump(self.rules, default_flow_style=False, sort_keys=False))

    def _default_rules(self) -> dict:
        return {
            "version": "2.5",
            "global": {
                "max_spend_autonomous": 50,
                "max_spend_notify": 500,
                "max_emails_per_hour": 10,
                "max_alerts_per_hour": 5,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
                "quiet_hours_action": "batch",
                "default_level": "notify"
            },
            "actions": {
                "alert": {
                    "sms": {"level": "autonomous", "conditions": ["urgency >= high"]},
                    "email": {"level": "notify", "conditions": []}
                },
                "research": {
                    "web_search": {"level": "autonomous", "conditions": []},
                    "prospect_research": {"level": "autonomous", "conditions": []}
                },
                "communication": {
                    "draft_email": {"level": "autonomous", "conditions": []},
                    "send_email": {"level": "approval_required", "conditions": []}
                },
                "code": {
                    "read_only": {"level": "autonomous", "conditions": []},
                    "write_files": {"level": "notify", "conditions": []},
                    "deploy": {"level": "approval_required", "conditions": []}
                },
                "financial": {
                    "analyze": {"level": "autonomous", "conditions": []},
                    "generate_invoice": {"level": "notify", "conditions": []},
                    "payment": {"level": "approval_required", "conditions": []}
                }
            },
            "agents": {
                "coyote": {"trust_level": "high", "overrides": {}},
                "vega": {"trust_level": "high", "overrides": {}},
                "mason": {"trust_level": "medium", "overrides": {}},
                "prophet": {"trust_level": "medium", "overrides": {}},
                "sentinel": {"trust_level": "high", "overrides": {}},
                "arbiter": {"trust_level": "medium", "overrides": {}}
            },
            "escalation": {
                "always_escalate": [
                    "estimated_impact_usd > 10000",
                    "involves_external_legal",
                    "investor_communication",
                    "press_or_media"
                ],
                "method": {
                    "urgent": "sms",
                    "normal": "email",
                    "batch": "daily_digest"
                }
            }
        }

    def check_permission(
        self,
        agent_id: str,
        action_category: str,
        action_type: str,
        context: dict
    ) -> PermissionResult:
        """Check if an agent can perform an action"""
        conditions_met = []
        conditions_failed = []

        # Check quiet hours
        if self._in_quiet_hours():
            quiet_action = self.rules["global"].get("quiet_hours_action", "normal")
            if quiet_action == "emergency_only" and context.get("urgency") != "emergency":
                return PermissionResult(
                    allowed=False,
                    level=AutonomyLevel.APPROVAL_REQUIRED,
                    reason="Quiet hours - non-emergency actions batched",
                    conditions_met=[],
                    conditions_failed=["quiet_hours"]
                )

        # Check always-escalate conditions
        for condition in self.rules.get("escalation", {}).get("always_escalate", []):
            if self._evaluate_condition(condition, context):
                return PermissionResult(
                    allowed=False,
                    level=AutonomyLevel.APPROVAL_REQUIRED,
                    reason=f"Always escalate: {condition}",
                    conditions_met=[],
                    conditions_failed=[condition],
                    requires_approval_from="blake"
                )

        # Get base rule
        action_rules = self.rules.get("actions", {}).get(action_category, {}).get(action_type, {})
        base_level = action_rules.get("level", self.rules["global"]["default_level"])

        # Check agent overrides
        agent_rules = self.rules.get("agents", {}).get(agent_id, {}).get("overrides", {})
        action_key = f"{action_category}.{action_type}"
        if action_key in agent_rules:
            override = agent_rules[action_key]
            base_level = override.get("level", base_level)
            action_rules = {**action_rules, **override}

        # Evaluate conditions
        for condition in action_rules.get("conditions", []):
            if self._evaluate_condition(condition, context):
                conditions_met.append(condition)
            else:
                conditions_failed.append(condition)

        # Check approval_required_if
        for condition in action_rules.get("approval_required_if", []):
            if self._evaluate_condition(condition, context):
                return PermissionResult(
                    allowed=False,
                    level=AutonomyLevel.APPROVAL_REQUIRED,
                    reason=f"Requires approval: {condition}",
                    conditions_met=conditions_met,
                    conditions_failed=[condition],
                    requires_approval_from="blake"
                )

        # Check financial limits
        if "amount_usd" in context:
            amount = context["amount_usd"]
            max_auto = self.rules["global"]["max_spend_autonomous"]
            max_notify = self.rules["global"]["max_spend_notify"]

            if amount > max_notify:
                return PermissionResult(
                    allowed=False,
                    level=AutonomyLevel.APPROVAL_REQUIRED,
                    reason=f"Amount ${amount} exceeds limit ${max_notify}",
                    conditions_met=conditions_met,
                    conditions_failed=["financial_limit"],
                    requires_approval_from="blake"
                )
            elif amount > max_auto:
                base_level = "notify"

        level = AutonomyLevel(base_level)

        notify_via = None
        if level == AutonomyLevel.NOTIFY:
            notify_via = "email"
            if context.get("urgency") == "high":
                notify_via = "sms"

        return PermissionResult(
            allowed=(level != AutonomyLevel.APPROVAL_REQUIRED),
            level=level,
            reason=f"Action permitted at {level.value} level",
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            notify_via=notify_via
        )

    def _in_quiet_hours(self) -> bool:
        now = datetime.now().time()
        start = datetime.strptime(
            self.rules["global"].get("quiet_hours_start", "22:00"),
            "%H:%M"
        ).time()
        end = datetime.strptime(
            self.rules["global"].get("quiet_hours_end", "07:00"),
            "%H:%M"
        ).time()

        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        try:
            if " == " in condition:
                key, value = condition.split(" == ")
                return str(context.get(key.strip())) == value.strip().strip('"\'')
            if " != " in condition:
                key, value = condition.split(" != ")
                return str(context.get(key.strip())) != value.strip().strip('"\'')
            if " >= " in condition:
                key, value = condition.split(" >= ")
                ctx_val = context.get(key.strip())
                if ctx_val is None:
                    return False
                # Handle string comparisons for urgency levels
                if key.strip() == "urgency":
                    levels = {"low": 1, "medium": 2, "high": 3, "critical": 4, "emergency": 5}
                    ctx_level = levels.get(str(ctx_val).lower(), 0)
                    threshold = levels.get(value.strip().lower(), 0)
                    return ctx_level >= threshold
                return float(ctx_val) >= float(value.strip())
            if " > " in condition:
                key, value = condition.split(" > ")
                ctx_val = context.get(key.strip())
                if ctx_val is None:
                    return False
                return float(ctx_val) > float(value.strip())
            if " in [" in condition:
                key, rest = condition.split(" in [")
                values = [v.strip().strip('"\'') for v in rest.rstrip("]").split(",")]
                return str(context.get(key.strip())) in values
            return bool(context.get(condition.strip()))
        except Exception:
            return False

    def request_approval(
        self,
        agent_id: str,
        action_description: str,
        context: dict,
        audit_id: str
    ) -> str:
        """Create approval request, return request ID"""
        import uuid
        request_id = str(uuid.uuid4())[:8]

        pending_file = self.workspace / "pending_approvals.jsonl"
        with open(pending_file, "a") as f:
            f.write(json.dumps({
                "request_id": request_id,
                "audit_id": audit_id,
                "agent_id": agent_id,
                "action": action_description,
                "context": context,
                "requested_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }) + "\n")

        return request_id

    def get_pending_approvals(self) -> List[dict]:
        """Get all pending approval requests"""
        pending_file = self.workspace / "pending_approvals.jsonl"
        if not pending_file.exists():
            return []

        approvals = []
        for line in pending_file.read_text().strip().split("\n"):
            if line:
                approval = json.loads(line)
                if approval.get("status") == "pending":
                    approvals.append(approval)
        return approvals

    def approve_request(self, request_id: str, approver: str = "blake") -> bool:
        """Approve a pending request"""
        return self._update_request_status(request_id, "approved", approver)

    def reject_request(self, request_id: str, approver: str = "blake", reason: str = "") -> bool:
        """Reject a pending request"""
        return self._update_request_status(request_id, "rejected", approver, reason)

    def _update_request_status(
        self,
        request_id: str,
        status: str,
        approver: str,
        reason: str = ""
    ) -> bool:
        """Update the status of a pending request"""
        pending_file = self.workspace / "pending_approvals.jsonl"
        if not pending_file.exists():
            return False

        lines = pending_file.read_text().strip().split("\n")
        updated = False
        new_lines = []

        for line in lines:
            if not line:
                continue
            approval = json.loads(line)
            if approval.get("request_id") == request_id:
                approval["status"] = status
                approval["resolved_by"] = approver
                approval["resolved_at"] = datetime.utcnow().isoformat()
                if reason:
                    approval["rejection_reason"] = reason
                updated = True
            new_lines.append(json.dumps(approval))

        if updated:
            pending_file.write_text("\n".join(new_lines) + "\n")

        return updated
