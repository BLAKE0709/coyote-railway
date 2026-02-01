"""
COYOTE V2.5 - Heartbeat Service

Periodic checks and monitoring. Runs every 30 minutes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Callable
from pathlib import Path
import json


@dataclass
class HeartbeatCheck:
    """Result of a single check"""
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class HeartbeatResult:
    """Result of a full heartbeat run"""
    timestamp: datetime
    overall_status: str
    checks: List[HeartbeatCheck]
    duration_ms: float
    actions_taken: List[str]


class HeartbeatService:
    """Runs periodic health checks and maintenance"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.config_path = workspace_path / "HEARTBEAT.md"
        self.history_path = workspace_path / "heartbeat_history.jsonl"
        self.checks: List[Callable[[], HeartbeatCheck]] = []
        self._ensure_config()
        self._register_default_checks()

    def _ensure_config(self):
        """Ensure heartbeat config exists"""
        if not self.config_path.exists():
            self.config_path.write_text("""# COYOTE Heartbeat Configuration

## Schedule
- Interval: 30 minutes
- Quiet hours: 10 PM - 7 AM (reduced checks)

## Checks
1. System health
2. Pending approvals
3. Outcome tracking
4. Budget status
5. Memory cleanup

## Alert Thresholds
- Budget: Alert at 80% usage
- Pending approvals: Alert if > 5 waiting
- Outcomes: Alert if tracking rate < 50%
""")

    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check(self._check_workspace)
        self.register_check(self._check_pending_approvals)
        self.register_check(self._check_audit_health)

    def register_check(self, check_fn: Callable[[], HeartbeatCheck]):
        """Register a new health check"""
        self.checks.append(check_fn)

    def _check_workspace(self) -> HeartbeatCheck:
        """Check workspace directory health"""
        try:
            # Check if key directories exist
            required_dirs = ["audit", "costs", "memory", "skills"]
            missing = [d for d in required_dirs if not (self.workspace / d).exists()]

            if missing:
                return HeartbeatCheck(
                    name="workspace",
                    status="warning",
                    message=f"Missing directories: {', '.join(missing)}"
                )

            return HeartbeatCheck(
                name="workspace",
                status="ok",
                message="All directories present"
            )
        except Exception as e:
            return HeartbeatCheck(
                name="workspace",
                status="error",
                message=str(e)
            )

    def _check_pending_approvals(self) -> HeartbeatCheck:
        """Check for stale pending approvals"""
        try:
            pending_file = self.workspace / "pending_approvals.jsonl"
            if not pending_file.exists():
                return HeartbeatCheck(
                    name="pending_approvals",
                    status="ok",
                    message="No pending approvals",
                    value=0
                )

            pending_count = 0
            stale_count = 0
            cutoff = datetime.utcnow() - timedelta(hours=24)

            for line in pending_file.read_text().strip().split("\n"):
                if not line:
                    continue
                approval = json.loads(line)
                if approval.get("status") == "pending":
                    pending_count += 1
                    requested_at = datetime.fromisoformat(approval["requested_at"])
                    if requested_at < cutoff:
                        stale_count += 1

            if stale_count > 0:
                return HeartbeatCheck(
                    name="pending_approvals",
                    status="warning",
                    message=f"{stale_count} approvals waiting > 24 hours",
                    value=pending_count,
                    threshold=5
                )

            if pending_count > 5:
                return HeartbeatCheck(
                    name="pending_approvals",
                    status="warning",
                    message=f"{pending_count} approvals pending",
                    value=pending_count,
                    threshold=5
                )

            return HeartbeatCheck(
                name="pending_approvals",
                status="ok",
                message=f"{pending_count} pending",
                value=pending_count
            )

        except Exception as e:
            return HeartbeatCheck(
                name="pending_approvals",
                status="error",
                message=str(e)
            )

    def _check_audit_health(self) -> HeartbeatCheck:
        """Check audit trail health"""
        try:
            audit_dir = self.workspace / "audit"
            if not audit_dir.exists():
                return HeartbeatCheck(
                    name="audit",
                    status="warning",
                    message="Audit directory missing"
                )

            # Check for recent entries
            today_file = audit_dir / f"{datetime.utcnow().date().isoformat()}.jsonl"
            if not today_file.exists():
                return HeartbeatCheck(
                    name="audit",
                    status="ok",
                    message="No entries today (may be normal)"
                )

            entry_count = len(today_file.read_text().strip().split("\n"))
            return HeartbeatCheck(
                name="audit",
                status="ok",
                message=f"{entry_count} entries today",
                value=entry_count
            )

        except Exception as e:
            return HeartbeatCheck(
                name="audit",
                status="error",
                message=str(e)
            )

    def run(self) -> HeartbeatResult:
        """Run all health checks"""
        start = datetime.utcnow()
        checks = []
        actions = []

        for check_fn in self.checks:
            try:
                result = check_fn()
                checks.append(result)
            except Exception as e:
                checks.append(HeartbeatCheck(
                    name=check_fn.__name__,
                    status="error",
                    message=str(e)
                ))

        # Determine overall status
        if any(c.status == "error" for c in checks):
            overall = "error"
        elif any(c.status == "warning" for c in checks):
            overall = "warning"
        else:
            overall = "ok"

        duration = (datetime.utcnow() - start).total_seconds() * 1000

        result = HeartbeatResult(
            timestamp=start,
            overall_status=overall,
            checks=checks,
            duration_ms=duration,
            actions_taken=actions
        )

        # Record to history
        self._record_heartbeat(result)

        return result

    def _record_heartbeat(self, result: HeartbeatResult):
        """Record heartbeat result to history"""
        with open(self.history_path, "a") as f:
            f.write(json.dumps({
                "timestamp": result.timestamp.isoformat(),
                "overall_status": result.overall_status,
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "message": c.message,
                        "value": c.value
                    }
                    for c in result.checks
                ],
                "duration_ms": result.duration_ms,
                "actions_taken": result.actions_taken
            }) + "\n")

    def get_recent_heartbeats(self, count: int = 10) -> List[dict]:
        """Get recent heartbeat results"""
        if not self.history_path.exists():
            return []

        lines = self.history_path.read_text().strip().split("\n")
        results = []
        for line in reversed(lines[-count:]):
            if line:
                results.append(json.loads(line))

        return results

    def get_status_summary(self) -> dict:
        """Get current status summary"""
        recent = self.get_recent_heartbeats(24)  # Last 24 heartbeats (12 hours at 30min interval)

        if not recent:
            return {"status": "unknown", "message": "No heartbeat data"}

        latest = recent[0]
        error_count = sum(1 for h in recent if h["overall_status"] == "error")
        warning_count = sum(1 for h in recent if h["overall_status"] == "warning")

        return {
            "status": latest["overall_status"],
            "last_check": latest["timestamp"],
            "checks_in_period": len(recent),
            "errors": error_count,
            "warnings": warning_count,
            "uptime_percent": ((len(recent) - error_count) / len(recent)) * 100 if recent else 0
        }
