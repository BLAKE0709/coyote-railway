"""
COYOTE V2.5 - Integrated Swarm Agent

Brings all modules together into a cohesive agent that processes tasks
through the full governance pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import json
import re

from .config import Config
from .memory import MemoryManager, Memory
from .alerts import AlertService
from .audit import (
    AuditTrail, AuditEntry, TriggerType, ActionType,
    ActionResult, AutonomyLevel
)
from .autonomy import AutonomyEngine, PermissionResult
from .outcomes import OutcomeTracker
from .router import ModelRouter, RoutingDecision
from .skills import SkillsManager, LoadedSkill
from .heartbeat import HeartbeatService


@dataclass
class AgentResponse:
    """Response from agent processing"""
    success: bool
    audit_id: str
    decision: str
    action_taken: Optional[str]
    autonomy_level: AutonomyLevel
    model_used: str
    cost_usd: float
    skills_used: List[str]
    error: Optional[str] = None


class CoyoteAgent:
    """
    COYOTE V2.5 - Swarm Orchestration Agent

    Integrates:
    - Audit Trail (logging)
    - Autonomy Rules (governance)
    - Outcome Tracking (learning)
    - Multi-Model Routing (efficiency)
    - Skills Framework (capabilities)
    - Memory System (context)
    - Alert Service (notifications)
    - Heartbeat (monitoring)
    """

    def __init__(self, config: Config):
        self.config = config
        self.workspace = config.workspace_path

        # Initialize all modules
        self.memory = MemoryManager(self.workspace)
        self.alerts = AlertService(config)
        self.audit = AuditTrail(self.workspace)
        self.autonomy = AutonomyEngine(self.workspace)
        self.outcomes = OutcomeTracker(self.workspace, self.audit)
        self.router = ModelRouter(self.workspace)
        self.skills = SkillsManager(self.workspace)
        self.heartbeat = HeartbeatService(self.workspace)

        # Anthropic client (lazy init)
        self._client = None

    @property
    def client(self):
        """Lazy initialize Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            except ImportError:
                raise RuntimeError("anthropic library not installed")
        return self._client

    def process(
        self,
        input_text: str,
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_source: str = "",
        requesting_agent: str = "coyote",
        parent_audit_id: Optional[str] = None,
        force_model: Optional[str] = None
    ) -> AgentResponse:
        """
        Main processing pipeline for any agent request.

        Pipeline:
        1. Detect relevant skills
        2. Route to appropriate model
        3. Build context with skills and memories
        4. Get model response
        5. Parse decision and action
        6. Check autonomy rules
        7. Execute if permitted
        8. Log to audit trail
        """

        # Create audit entry
        entry = AuditEntry(
            agent_id=requesting_agent,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            parent_audit_id=parent_audit_id,
            context_summary=input_text[:200]
        )

        try:
            # 1. Detect and load relevant skills
            skill_ids = self.skills.detect_relevant_skills(input_text)
            loaded_skills = self.skills.load_skills(skill_ids)
            entry.skills_loaded = [s.id for s in loaded_skills]

            # 2. Load relevant memories
            memories = self.memory.search(input_text, limit=5)
            entry.memory_retrieved = [m.id for m in memories]

            # 3. Route to appropriate model
            routing = self.router.route(
                agent_id=requesting_agent,
                task_description=input_text,
                force_model=force_model
            )
            entry.model_used = routing.model

            # 4. Build prompt with skills and memories
            system_prompt = self._build_system_prompt(loaded_skills, memories)

            # 5. Get model response
            response = self.client.messages.create(
                model=routing.model_id,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": input_text}]
            )

            # 6. Parse response for decision and action
            response_text = response.content[0].text
            decision, action_type, action_details = self._parse_response(response_text)

            entry.decision = decision
            entry.reasoning = response_text[:500]
            entry.action_type = action_type
            entry.action_details = action_details

            # 7. Record token usage
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            entry.tokens_used = input_tokens + output_tokens
            entry.cost_usd = self.router.record_usage(
                requesting_agent,
                routing.model,
                input_tokens,
                output_tokens
            )

            # 8. Check autonomy rules
            permission = self.autonomy.check_permission(
                agent_id=requesting_agent,
                action_category=self._get_action_category(action_type),
                action_type=action_type.value,
                context={
                    "action_details": action_details,
                    "confidence": entry.confidence,
                    **action_details
                }
            )
            entry.autonomy_level = permission.level

            # 9. Execute action if permitted
            if permission.allowed:
                result = self._execute_action(action_type, action_details, permission)
                entry.action_result = ActionResult.SUCCESS if result else ActionResult.FAILURE

                # Notify if required
                if permission.level == AutonomyLevel.NOTIFY:
                    self._send_notification(entry, permission)
            else:
                # Request approval
                entry.action_result = ActionResult.AWAITING_APPROVAL
                self.autonomy.request_approval(
                    requesting_agent,
                    f"{action_type.value}: {decision}",
                    action_details,
                    entry.id
                )

            # 10. Log to audit trail
            self.audit.log_action(entry)

            return AgentResponse(
                success=True,
                audit_id=entry.id,
                decision=decision,
                action_taken=action_type.value if permission.allowed else None,
                autonomy_level=permission.level,
                model_used=routing.model,
                cost_usd=entry.cost_usd,
                skills_used=entry.skills_loaded
            )

        except Exception as e:
            entry.action_result = ActionResult.FAILURE
            entry.error_message = str(e)
            self.audit.log_action(entry)

            return AgentResponse(
                success=False,
                audit_id=entry.id,
                decision="Error during processing",
                action_taken=None,
                autonomy_level=AutonomyLevel.NOTIFY,
                model_used=entry.model_used,
                cost_usd=entry.cost_usd,
                skills_used=entry.skills_loaded,
                error=str(e)
            )

    def _build_system_prompt(
        self,
        skills: List[LoadedSkill],
        memories: List[Memory]
    ) -> str:
        """Build system prompt with loaded skills and memories"""
        parts = [
            "You are COYOTE, Blake's AI Chief of Staff and swarm orchestrator.",
            "You coordinate all agent activities and make decisions on Blake's behalf.",
            "",
            "## Current Context"
        ]

        # Add core memory
        core_memory = self.memory.get_core_memory()
        parts.append("\n### Core Memory")
        parts.append(core_memory[:2000])  # Limit size

        # Add recent memories
        if memories:
            parts.append("\n### Relevant Memories")
            for mem in memories:
                parts.append(f"- [{mem.category}] {mem.content}")

        # Add skills
        if skills:
            parts.append("\n### Loaded Skills")
            for skill in skills:
                parts.append(f"\n#### {skill.name}")
                parts.append(skill.content[:1000])  # Limit each skill

        # Add response format
        parts.append("""
## Response Format

Analyze the input and respond with:

1. **Decision**: What should be done (1-2 sentences)
2. **Action**: One of [alert, email, api_call, code_execution, delegate, log_only]
3. **Details**: Specific action parameters as JSON

Example:
```
Decision: Send Blake an alert about the revenue opportunity
Action: alert
Details: {"type": "sms", "urgency": "high", "message": "New $50K opportunity from Quikrete"}
```

If no action is needed, use Action: log_only
""")

        return "\n".join(parts)

    def _parse_response(self, response_text: str):
        """Parse model response into decision, action type, and details"""
        decision = ""
        action_type = ActionType.LOG_ONLY
        action_details = {}

        lines = response_text.split("\n")
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            if line_lower.startswith("decision:"):
                decision = line.split(":", 1)[1].strip()

            elif line_lower.startswith("action:"):
                action_str = line.split(":", 1)[1].strip().lower()
                # Clean up action string
                action_str = action_str.replace("*", "").strip()
                try:
                    action_type = ActionType(action_str)
                except ValueError:
                    action_type = ActionType.LOG_ONLY

            elif line_lower.startswith("details:"):
                # Look for JSON on same line or following lines
                details_str = line.split(":", 1)[1].strip()

                # Try to find JSON block
                if not details_str or details_str == "{":
                    # Look for JSON in subsequent lines
                    json_lines = []
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if next_line.startswith("```"):
                            continue
                        json_lines.append(next_line)
                        if next_line.endswith("}"):
                            break
                    details_str = " ".join(json_lines)

                try:
                    # Clean up JSON string
                    details_str = re.sub(r'```json?', '', details_str)
                    details_str = re.sub(r'```', '', details_str)
                    action_details = json.loads(details_str)
                except (json.JSONDecodeError, TypeError):
                    pass

        # If no decision found, use first substantial line
        if not decision:
            for line in lines:
                if len(line.strip()) > 20:
                    decision = line.strip()[:200]
                    break

        return decision, action_type, action_details

    def _get_action_category(self, action_type: ActionType) -> str:
        """Map action type to category for autonomy rules"""
        mapping = {
            ActionType.ALERT: "alert",
            ActionType.EMAIL: "communication",
            ActionType.API_CALL: "code",
            ActionType.CODE_EXECUTION: "code",
            ActionType.CLAUDE_CODE: "code",
            ActionType.DELEGATE: "communication",
            ActionType.APPROVAL_REQUEST: "communication",
            ActionType.LOG_ONLY: "research"
        }
        return mapping.get(action_type, "research")

    def _execute_action(
        self,
        action_type: ActionType,
        details: dict,
        permission: PermissionResult
    ) -> bool:
        """Execute the action"""
        if action_type == ActionType.ALERT:
            alert_type = details.get("type", "sms")
            if alert_type == "sms":
                return self.alerts.send_sms(
                    details.get("message", "COYOTE Alert"),
                    urgency=details.get("urgency", "normal")
                )
            return False

        elif action_type == ActionType.EMAIL:
            # Would integrate with email service
            # For now, just log
            print(f"EMAIL would be sent: {details}")
            return True

        elif action_type == ActionType.DELEGATE:
            # Delegate to another agent
            target_agent = details.get("agent")
            task = details.get("task")
            if target_agent and task:
                # Recursive call with new agent
                result = self.process(
                    task,
                    trigger_type=TriggerType.AGENT_REQUEST,
                    trigger_source="delegated_from_coyote",
                    requesting_agent=target_agent
                )
                return result.success
            return False

        elif action_type == ActionType.LOG_ONLY:
            return True

        return False

    def _send_notification(self, entry: AuditEntry, permission: PermissionResult):
        """Send notification about action taken"""
        if permission.notify_via == "sms":
            message = f"COYOTE {entry.action_type.value}: {entry.decision[:100]}"
            self.alerts.send_sms(message, urgency="normal")

    def run_heartbeat(self) -> AgentResponse:
        """
        Run periodic heartbeat check.
        Updates outcome tracking and performs routine checks.
        """
        # Check pending outcomes
        self.outcomes.check_pending_outcomes()

        # Run heartbeat checks
        heartbeat_result = self.heartbeat.run()

        # Process through agent pipeline
        status_summary = f"Heartbeat: {heartbeat_result.overall_status}. "
        status_summary += f"{len(heartbeat_result.checks)} checks run."

        if heartbeat_result.overall_status != "ok":
            # Get details of non-ok checks
            issues = [c for c in heartbeat_result.checks if c.status != "ok"]
            for issue in issues[:3]:
                status_summary += f" {issue.name}: {issue.message}."

        return self.process(
            f"Heartbeat check complete. {status_summary}",
            trigger_type=TriggerType.HEARTBEAT,
            trigger_source="30min_heartbeat"
        )

    def get_status(self) -> dict:
        """Get current agent status"""
        return {
            "config_valid": self.config.is_valid(),
            "integrations": self.config.validate(),
            "audit_stats": self.audit.get_stats(days=1),
            "budget_status": self.router.get_today_status(),
            "heartbeat": self.heartbeat.get_status_summary(),
            "pending_approvals": len(self.autonomy.get_pending_approvals())
        }
