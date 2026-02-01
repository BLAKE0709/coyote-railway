"""
COYOTE V2.5 - Multi-Model Routing

Use the right model for the job. Haiku for quick tasks, Opus for complex reasoning.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Tuple, List
from pathlib import Path
import yaml
import json
import re


@dataclass
class RoutingDecision:
    model: str
    model_id: str
    reason: str
    estimated_cost: float
    within_budget: bool


@dataclass
class CostTracker:
    daily_total: float = 0.0
    by_agent: dict = None
    by_model: dict = None

    def __post_init__(self):
        self.by_agent = self.by_agent or {}
        self.by_model = self.by_model or {}


class ModelRouter:
    """Routes tasks to appropriate models based on complexity and budget"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.config_path = workspace_path / "model_config.yaml"
        self.costs_dir = workspace_path / "costs"
        self.costs_dir.mkdir(exist_ok=True)
        self._load_config()
        self._load_daily_costs()

    def _load_config(self):
        if self.config_path.exists():
            self.config = yaml.safe_load(self.config_path.read_text())
        else:
            self.config = self._default_config()
            self._save_config()

    def _save_config(self):
        self.config_path.write_text(yaml.dump(self.config, default_flow_style=False))

    def _default_config(self) -> dict:
        return {
            "version": "2.5",
            "models": {
                "haiku": {
                    "id": "claude-3-5-haiku-20241022",
                    "cost_per_million_input": 0.25,
                    "cost_per_million_output": 1.25,
                    "max_tokens": 8192,
                    "strengths": ["quick lookups", "simple formatting", "data extraction", "classification"]
                },
                "sonnet": {
                    "id": "claude-sonnet-4-20250514",
                    "cost_per_million_input": 3.00,
                    "cost_per_million_output": 15.00,
                    "max_tokens": 16384,
                    "strengths": ["balanced reasoning", "code generation", "email drafting", "analysis"]
                },
                "opus": {
                    "id": "claude-opus-4-20250514",
                    "cost_per_million_input": 15.00,
                    "cost_per_million_output": 75.00,
                    "max_tokens": 32768,
                    "strengths": ["complex reasoning", "strategic decisions", "nuanced communication"]
                }
            },
            "routing": {
                "default": "sonnet",
                "by_task_type": [
                    {"pattern": "classify|categorize|extract|lookup|format|parse|list|count", "model": "haiku"},
                    {"pattern": "draft|write|analyze|summarize|code|review|explain", "model": "sonnet"},
                    {"pattern": "strategic|negotiate|complex|critical|investor|legal|synthesize", "model": "opus"}
                ],
                "by_agent": {
                    "coyote": "sonnet",
                    "vega": "sonnet",
                    "mason": "haiku",
                    "prophet": "haiku",
                    "sentinel": "haiku",
                    "arbiter": "sonnet"
                },
                "complexity_thresholds": [
                    {"max_tokens": 500, "model": "haiku"},
                    {"max_tokens": 2000, "model": "sonnet"},
                    {"max_tokens": 10000, "model": "opus"}
                ]
            },
            "budget": {
                "daily_limit_usd": 50.00,
                "alert_at_percent": 80,
                "agent_limits": {
                    "coyote": 20.00,
                    "vega": 10.00,
                    "mason": 5.00,
                    "prophet": 5.00,
                    "sentinel": 5.00,
                    "arbiter": 5.00
                }
            },
            "overrides": {
                "force_opus": ["investor meeting", "board presentation", "strategic decision"],
                "never_opus": ["routine check", "status update", "simple lookup"],
                "force_haiku": ["heartbeat", "monitoring", "log parsing"]
            }
        }

    def _load_daily_costs(self):
        today_file = self.costs_dir / f"{date.today().isoformat()}.json"
        if today_file.exists():
            data = json.loads(today_file.read_text())
            self.costs = CostTracker(**data)
        else:
            self.costs = CostTracker()

    def _save_daily_costs(self):
        today_file = self.costs_dir / f"{date.today().isoformat()}.json"
        today_file.write_text(json.dumps({
            "daily_total": self.costs.daily_total,
            "by_agent": self.costs.by_agent,
            "by_model": self.costs.by_model
        }, indent=2))

    def route(
        self,
        agent_id: str,
        task_description: str,
        estimated_tokens: int = 1000,
        force_model: Optional[str] = None
    ) -> RoutingDecision:
        """Determine which model to use for a task"""
        # Check override rules first
        task_lower = task_description.lower()

        # Force model if specified
        if force_model and force_model in self.config["models"]:
            model = force_model
            reason = "Model explicitly specified"
        else:
            model = None
            reason = ""

            # Check force_opus keywords
            for keyword in self.config.get("overrides", {}).get("force_opus", []):
                if keyword.lower() in task_lower:
                    model = "opus"
                    reason = f"Force Opus: contains '{keyword}'"
                    break

            # Check force_haiku keywords if no opus match
            if model is None:
                for keyword in self.config.get("overrides", {}).get("force_haiku", []):
                    if keyword.lower() in task_lower:
                        model = "haiku"
                        reason = f"Force Haiku: contains '{keyword}'"
                        break

            # Normal routing if no override matched
            if model is None:
                model, reason = self._select_model(agent_id, task_description, estimated_tokens)

        # Get model details
        model_config = self.config["models"][model]
        model_id = model_config["id"]

        # Estimate cost (assuming 1:2 input:output ratio)
        input_cost = (estimated_tokens * 0.5) * model_config["cost_per_million_input"] / 1_000_000
        output_cost = estimated_tokens * model_config["cost_per_million_output"] / 1_000_000
        estimated_cost = input_cost + output_cost

        # Check budget
        daily_limit = self.config["budget"]["daily_limit_usd"]
        agent_limit = self.config["budget"].get("agent_limits", {}).get(agent_id, daily_limit)

        agent_spent = self.costs.by_agent.get(agent_id, 0)
        within_budget = (
            self.costs.daily_total + estimated_cost <= daily_limit and
            agent_spent + estimated_cost <= agent_limit
        )

        # Downgrade if over budget
        if not within_budget and model != "haiku":
            # Check if blocked by never_opus rule
            if model == "opus" and any(kw.lower() in task_lower for kw in self.config.get("overrides", {}).get("never_opus", [])):
                pass  # Already shouldn't be opus

            model = "haiku"
            model_config = self.config["models"]["haiku"]
            model_id = model_config["id"]
            input_cost = (estimated_tokens * 0.5) * model_config["cost_per_million_input"] / 1_000_000
            output_cost = estimated_tokens * model_config["cost_per_million_output"] / 1_000_000
            estimated_cost = input_cost + output_cost
            reason = "Downgraded to Haiku due to budget constraints"
            within_budget = True

        return RoutingDecision(
            model=model,
            model_id=model_id,
            reason=reason,
            estimated_cost=estimated_cost,
            within_budget=within_budget
        )

    def _select_model(
        self,
        agent_id: str,
        task_description: str,
        estimated_tokens: int
    ) -> Tuple[str, str]:
        """Select model based on routing rules"""
        routing = self.config.get("routing", {})

        # Check agent-specific routing
        agent_model = routing.get("by_agent", {}).get(agent_id)
        if agent_model:
            return agent_model, f"Agent {agent_id} default: {agent_model}"

        # Check task type patterns
        task_lower = task_description.lower()
        for rule in routing.get("by_task_type", []):
            pattern = rule.get("pattern", "")
            if re.search(pattern, task_lower):
                return rule["model"], f"Task matches pattern: {pattern}"

        # Check complexity thresholds
        for threshold in routing.get("complexity_thresholds", []):
            if estimated_tokens <= threshold["max_tokens"]:
                return threshold["model"], f"Token count ({estimated_tokens}) within {threshold['model']} range"

        # Default
        return routing.get("default", "sonnet"), "Default routing"

    def record_usage(
        self,
        agent_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Record actual usage and return cost"""
        model_config = self.config["models"].get(model, self.config["models"]["sonnet"])

        input_cost = input_tokens * model_config["cost_per_million_input"] / 1_000_000
        output_cost = output_tokens * model_config["cost_per_million_output"] / 1_000_000
        total_cost = input_cost + output_cost

        # Update tracking
        self.costs.daily_total += total_cost
        self.costs.by_agent[agent_id] = self.costs.by_agent.get(agent_id, 0) + total_cost
        self.costs.by_model[model] = self.costs.by_model.get(model, 0) + total_cost

        self._save_daily_costs()

        # Check alert threshold
        daily_limit = self.config["budget"]["daily_limit_usd"]
        alert_percent = self.config["budget"].get("alert_at_percent", 80)
        if self.costs.daily_total / daily_limit >= alert_percent / 100:
            self._trigger_budget_alert()

        return total_cost

    def _trigger_budget_alert(self):
        """Trigger budget alert (would integrate with alerts)"""
        daily_limit = self.config["budget"]["daily_limit_usd"]
        percent_used = (self.costs.daily_total / daily_limit) * 100
        # Log for now, would integrate with AlertService
        print(f"BUDGET ALERT: {percent_used:.1f}% of daily limit used (${self.costs.daily_total:.2f}/${daily_limit:.2f})")

    def get_cost_summary(self, days: int = 7) -> dict:
        """Get cost summary for recent period"""
        summary = {
            "period_days": days,
            "total_cost": 0,
            "by_day": {},
            "by_agent": {},
            "by_model": {},
            "daily_average": 0,
            "budget_utilization": 0
        }

        for i in range(days):
            day = date.today() - timedelta(days=i)
            day_file = self.costs_dir / f"{day.isoformat()}.json"
            if day_file.exists():
                data = json.loads(day_file.read_text())
                summary["by_day"][day.isoformat()] = data["daily_total"]
                summary["total_cost"] += data["daily_total"]

                for agent, cost in data.get("by_agent", {}).items():
                    summary["by_agent"][agent] = summary["by_agent"].get(agent, 0) + cost

                for model, cost in data.get("by_model", {}).items():
                    summary["by_model"][model] = summary["by_model"].get(model, 0) + cost

        if days > 0:
            summary["daily_average"] = summary["total_cost"] / days
            daily_limit = self.config["budget"]["daily_limit_usd"]
            summary["budget_utilization"] = summary["daily_average"] / daily_limit

        return summary

    def get_today_status(self) -> dict:
        """Get today's budget status"""
        daily_limit = self.config["budget"]["daily_limit_usd"]
        return {
            "date": date.today().isoformat(),
            "spent": self.costs.daily_total,
            "limit": daily_limit,
            "remaining": daily_limit - self.costs.daily_total,
            "percent_used": (self.costs.daily_total / daily_limit) * 100,
            "by_agent": self.costs.by_agent.copy(),
            "by_model": self.costs.by_model.copy()
        }

    def get_agent_budget_status(self, agent_id: str) -> dict:
        """Get budget status for a specific agent"""
        agent_limit = self.config["budget"].get("agent_limits", {}).get(agent_id, 10.0)
        agent_spent = self.costs.by_agent.get(agent_id, 0)
        return {
            "agent_id": agent_id,
            "spent": agent_spent,
            "limit": agent_limit,
            "remaining": agent_limit - agent_spent,
            "percent_used": (agent_spent / agent_limit) * 100 if agent_limit > 0 else 0
        }
