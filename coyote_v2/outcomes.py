"""
COYOTE V2.5 - Outcome Tracking

Track what happens after actions. Did Blake act on alerts? Did emails get responses?
This data feeds learning and autonomy adjustments.
"""

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Optional, List
from pathlib import Path

from .audit import AuditTrail, AuditEntry, OutcomeStatus, ActionResult


@dataclass
class DetectedOutcome:
    status: OutcomeStatus
    value_usd: Optional[float] = None
    notes: Optional[str] = None


class OutcomeHeuristic:
    """Base class for outcome detection heuristics"""

    def applies_to(self, action_type: str) -> bool:
        raise NotImplementedError

    def detect(self, audit_id: str, workspace: Path) -> Optional[DetectedOutcome]:
        raise NotImplementedError


class AlertResponseHeuristic(OutcomeHeuristic):
    """Detect if Blake responded to an alert"""

    def applies_to(self, action_type: str) -> bool:
        return action_type == "alert"

    def detect(self, audit_id: str, workspace: Path) -> Optional[DetectedOutcome]:
        # Check for follow-up actions referencing this alert
        # This would integrate with SMS reply tracking
        return None


class EmailResponseHeuristic(OutcomeHeuristic):
    """Detect if an email got a response"""

    def applies_to(self, action_type: str) -> bool:
        return action_type == "email"

    def detect(self, audit_id: str, workspace: Path) -> Optional[DetectedOutcome]:
        # Would integrate with Gmail to check for replies
        return None


class ApprovalResponseHeuristic(OutcomeHeuristic):
    """Detect if an approval request was handled"""

    def applies_to(self, action_type: str) -> bool:
        return action_type == "approval_request"

    def detect(self, audit_id: str, workspace: Path) -> Optional[DetectedOutcome]:
        import json
        pending_file = workspace / "pending_approvals.jsonl"
        if not pending_file.exists():
            return None

        for line in pending_file.read_text().strip().split("\n"):
            if not line:
                continue
            approval = json.loads(line)
            if approval.get("audit_id") == audit_id:
                if approval.get("status") == "approved":
                    return DetectedOutcome(
                        status=OutcomeStatus.ACTED_ON,
                        notes="Approval granted"
                    )
                elif approval.get("status") == "rejected":
                    return DetectedOutcome(
                        status=OutcomeStatus.REJECTED,
                        notes=f"Approval denied: {approval.get('rejection_reason', '')}"
                    )

        return None


class OutcomeTracker:
    """Tracks outcomes of agent actions and calculates effectiveness"""

    def __init__(self, workspace_path: Path, audit_trail: AuditTrail):
        self.workspace = workspace_path
        self.audit = audit_trail
        self.outcomes_dir = workspace_path / "outcomes"
        self.outcomes_dir.mkdir(exist_ok=True)

        # Outcome detection heuristics
        self.heuristics: List[OutcomeHeuristic] = [
            AlertResponseHeuristic(),
            EmailResponseHeuristic(),
            ApprovalResponseHeuristic(),
        ]

    def check_pending_outcomes(self) -> int:
        """
        Check all pending outcomes and update where possible.
        Returns the number of outcomes updated.
        """
        pending = self.audit.get_pending_outcomes()
        updated_count = 0

        for item in pending:
            audit_id = item["id"]
            action_type = item["action_type"]
            timestamp = datetime.fromisoformat(item["timestamp"])

            # Skip if too recent (give time for outcome to occur)
            if datetime.utcnow() - timestamp < timedelta(hours=1):
                continue

            # Try each heuristic
            for heuristic in self.heuristics:
                if heuristic.applies_to(action_type):
                    outcome = heuristic.detect(audit_id, self.workspace)
                    if outcome:
                        self.audit.update_outcome(
                            audit_id,
                            status=outcome.status,
                            value_usd=outcome.value_usd,
                            notes=outcome.notes
                        )
                        updated_count += 1
                        break

            # If no outcome detected after 7 days, mark as unknown
            if datetime.utcnow() - timestamp > timedelta(days=7):
                self.audit.update_outcome(
                    audit_id,
                    status=OutcomeStatus.IGNORED,
                    notes="No outcome detected within 7 days"
                )
                updated_count += 1

        return updated_count

    def mark_outcome(
        self,
        audit_id: str,
        status: OutcomeStatus,
        value_usd: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Manually mark an outcome for an action"""
        return self.audit.update_outcome(audit_id, status, value_usd, notes)

    def get_effectiveness_report(
        self,
        agent_id: Optional[str] = None,
        days: int = 30
    ) -> dict:
        """Generate effectiveness report for an agent or all agents"""
        entries = self.audit.query(
            start_date=date.today() - timedelta(days=days),
            agent_id=agent_id,
            limit=10000
        )

        with_outcomes = [e for e in entries if e.outcome_status]

        if not with_outcomes:
            return {
                "message": "No outcome data available",
                "total_actions": len(entries),
                "outcomes_tracked": 0
            }

        report = {
            "period_days": days,
            "total_actions": len(entries),
            "outcomes_tracked": len(with_outcomes),
            "tracking_rate": len(with_outcomes) / len(entries) if entries else 0,
            "by_outcome": {},
            "by_action_type": {},
            "by_agent": {},
            "value_generated_usd": 0,
            "recommendations": []
        }

        for entry in with_outcomes:
            # By outcome status
            status = entry.outcome_status.value
            if status not in report["by_outcome"]:
                report["by_outcome"][status] = 0
            report["by_outcome"][status] += 1

            # By action type
            action = entry.action_type.value
            if action not in report["by_action_type"]:
                report["by_action_type"][action] = {"total": 0, "acted_on": 0}
            report["by_action_type"][action]["total"] += 1
            if entry.outcome_status == OutcomeStatus.ACTED_ON:
                report["by_action_type"][action]["acted_on"] += 1

            # By agent
            agent = entry.agent_id
            if agent not in report["by_agent"]:
                report["by_agent"][agent] = {"total": 0, "acted_on": 0}
            report["by_agent"][agent]["total"] += 1
            if entry.outcome_status == OutcomeStatus.ACTED_ON:
                report["by_agent"][agent]["acted_on"] += 1

            # Value tracking
            if entry.outcome_value_usd:
                report["value_generated_usd"] += entry.outcome_value_usd

        # Calculate effectiveness and generate recommendations
        for action, stats in report["by_action_type"].items():
            effectiveness = stats["acted_on"] / stats["total"] if stats["total"] else 0
            stats["effectiveness"] = effectiveness

            if effectiveness < 0.3 and stats["total"] >= 10:
                report["recommendations"].append(
                    f"Reduce {action} actions - only {effectiveness:.0%} acted upon"
                )
            elif effectiveness > 0.9 and stats["total"] >= 10:
                report["recommendations"].append(
                    f"{action} highly effective ({effectiveness:.0%}) - consider increasing autonomy"
                )

        for agent, stats in report["by_agent"].items():
            effectiveness = stats["acted_on"] / stats["total"] if stats["total"] else 0
            stats["effectiveness"] = effectiveness

        return report

    def get_agent_performance(self, agent_id: str, days: int = 30) -> dict:
        """Get detailed performance metrics for a specific agent"""
        entries = self.audit.query(
            start_date=date.today() - timedelta(days=days),
            agent_id=agent_id,
            limit=10000
        )

        if not entries:
            return {"message": f"No data for agent {agent_id}"}

        with_outcomes = [e for e in entries if e.outcome_status]

        performance = {
            "agent_id": agent_id,
            "period_days": days,
            "total_actions": len(entries),
            "outcomes_tracked": len(with_outcomes),
            "success_rate": 0.0,
            "acted_on_rate": 0.0,
            "total_cost_usd": sum(e.cost_usd for e in entries),
            "total_tokens": sum(e.tokens_used for e in entries),
            "value_generated_usd": sum(e.outcome_value_usd or 0 for e in with_outcomes),
            "models_used": {},
            "action_breakdown": {}
        }

        successes = sum(1 for e in entries if e.action_result == ActionResult.SUCCESS)
        acted_on = sum(1 for e in with_outcomes if e.outcome_status == OutcomeStatus.ACTED_ON)

        if entries:
            performance["success_rate"] = successes / len(entries)
        if with_outcomes:
            performance["acted_on_rate"] = acted_on / len(with_outcomes)

        # Model usage breakdown
        for entry in entries:
            model = entry.model_used or "unknown"
            if model not in performance["models_used"]:
                performance["models_used"][model] = {"count": 0, "cost": 0.0}
            performance["models_used"][model]["count"] += 1
            performance["models_used"][model]["cost"] += entry.cost_usd

        # Action type breakdown
        for entry in entries:
            action = entry.action_type.value
            if action not in performance["action_breakdown"]:
                performance["action_breakdown"][action] = 0
            performance["action_breakdown"][action] += 1

        return performance
