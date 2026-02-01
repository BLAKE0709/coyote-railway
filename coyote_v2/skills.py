"""
COYOTE V2.5 - Skills Framework

Dynamic capabilities that compound. Agents ARE skills.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path
import yaml


@dataclass
class LoadedSkill:
    id: str
    name: str
    content: str
    priority: int
    tokens_used: int
    source: str  # "agent", "domain", "workflow"


class SkillsManager:
    """Manages dynamic skills including agent skills"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.skills_dir = workspace_path / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        self.agents_dir = workspace_path / "agents"
        self.agents_dir.mkdir(exist_ok=True)
        self.index_path = self.skills_dir / "_index.yaml"
        self._load_index()

    def _load_index(self):
        if self.index_path.exists():
            self.index = yaml.safe_load(self.index_path.read_text())
        else:
            self.index = self._default_index()
            self._save_index()

    def _save_index(self):
        self.index_path.write_text(yaml.dump(self.index, default_flow_style=False, sort_keys=False))

    def _default_index(self) -> dict:
        return {
            "version": "2.5",
            "agent_skills": {
                "vega": {
                    "name": "VEGA - Strategic CFO",
                    "description": "Financial modeling, tax strategy, investor communications",
                    "triggers": ["financial", "investor", "tax", "revenue", "model", "valuation", "unit economics"],
                    "priority": 90,
                    "token_budget": 2000,
                    "agent_file": "agents/vega.md"
                },
                "mason": {
                    "name": "MASON - VP Business Development",
                    "description": "Prospect research, deal origination, site qualification",
                    "triggers": ["prospect", "lead", "site", "deal", "partner", "cement", "industrial"],
                    "priority": 85,
                    "token_budget": 1500,
                    "agent_file": "agents/mason.md"
                },
                "prophet": {
                    "name": "PROPHET - Lead Generation",
                    "description": "Permit scraping, contractor leads, market intelligence",
                    "triggers": ["permit", "contractor", "construction", "leads"],
                    "priority": 80,
                    "token_budget": 1000,
                    "agent_file": "agents/prophet.md"
                },
                "sentinel": {
                    "name": "SENTINEL - Monitoring",
                    "description": "System monitoring, alerting, anomaly detection",
                    "triggers": ["monitor", "alert", "system", "health", "anomaly"],
                    "priority": 95,
                    "token_budget": 500,
                    "agent_file": "agents/sentinel.md"
                },
                "arbiter": {
                    "name": "ARBITER - Government Contracting",
                    "description": "SAM.gov monitoring, RFP analysis, compliance",
                    "triggers": ["government", "contract", "rfp", "sam.gov", "federal", "compliance"],
                    "priority": 85,
                    "token_budget": 1500,
                    "agent_file": "agents/arbiter.md"
                }
            },
            "domain_skills": {
                "atlas_thermal": {
                    "name": "Atlas Industrial Context",
                    "description": "Thermal symbiosis, ORC technology, cement industry knowledge",
                    "triggers": ["atlas", "thermal", "orc", "waste heat", "cement", "midlothian", "quikrete"],
                    "priority": 100,
                    "token_budget": 1000,
                    "skill_file": "skills/atlas-thermal.md"
                }
            },
            "workflow_skills": {
                "deal_qualification": {
                    "name": "Deal Qualification Workflow",
                    "description": "Full process for qualifying a new industrial site",
                    "triggers": ["qualify site", "new prospect", "deal qualification"],
                    "priority": 90,
                    "token_budget": 1500,
                    "skill_file": "skills/deal-qualification.md",
                    "steps": ["MASON researches site", "VEGA models economics", "Review with Blake"]
                },
                "morning_briefing": {
                    "name": "Morning Briefing",
                    "description": "Daily status synthesis across all systems",
                    "triggers": ["morning", "briefing", "daily update", "status"],
                    "priority": 95,
                    "token_budget": 2000,
                    "skill_file": "skills/morning-briefing.md"
                }
            },
            "settings": {
                "max_skills_per_context": 5,
                "total_token_budget": 4000,
                "auto_detect": True,
                "log_skill_usage": True
            }
        }

    def detect_relevant_skills(self, context: str) -> List[str]:
        """Analyze context and return relevant skill IDs"""
        context_lower = context.lower()
        matches = []

        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            for skill_id, config in self.index.get(skill_type, {}).items():
                triggers = config.get("triggers", [])
                for trigger in triggers:
                    if trigger.lower() in context_lower:
                        matches.append({
                            "id": skill_id,
                            "type": skill_type,
                            "priority": config.get("priority", 50),
                            "trigger": trigger
                        })
                        break

        # Sort by priority (highest first) and dedupe
        matches.sort(key=lambda x: x["priority"], reverse=True)
        seen = set()
        unique = []
        for m in matches:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m["id"])

        max_skills = self.index["settings"]["max_skills_per_context"]
        return unique[:max_skills]

    def load_skills(self, skill_ids: List[str], token_budget: Optional[int] = None) -> List[LoadedSkill]:
        """Load skill content for given IDs"""
        budget = token_budget or self.index["settings"]["total_token_budget"]
        tokens_used = 0
        loaded = []

        for skill_id in skill_ids:
            config = None
            skill_type = None
            for st in ["agent_skills", "domain_skills", "workflow_skills"]:
                if skill_id in self.index.get(st, {}):
                    config = self.index[st][skill_id]
                    skill_type = st
                    break

            if not config:
                continue

            skill_tokens = config.get("token_budget", 500)
            if tokens_used + skill_tokens > budget:
                continue

            content = self._load_skill_content(skill_id, config, skill_type)
            if content:
                loaded.append(LoadedSkill(
                    id=skill_id,
                    name=config.get("name", skill_id),
                    content=content,
                    priority=config.get("priority", 50),
                    tokens_used=skill_tokens,
                    source=skill_type.replace("_skills", "")
                ))
                tokens_used += skill_tokens

        return loaded

    def _load_skill_content(self, skill_id: str, config: dict, skill_type: str) -> Optional[str]:
        """Load the actual skill content from file"""
        file_key = "agent_file" if skill_type == "agent_skills" else "skill_file"
        relative_path = config.get(file_key)
        if not relative_path:
            return None

        skill_path = self.workspace / relative_path
        if skill_path.exists():
            return skill_path.read_text()

        # Return a placeholder if file doesn't exist yet
        return f"# {config.get('name', skill_id)}\n\n{config.get('description', 'No description available.')}"

    def get_skills_for_agent(self, agent_id: str) -> Optional[LoadedSkill]:
        """Get skill definition for a specific agent"""
        if agent_id in self.index.get("agent_skills", {}):
            config = self.index["agent_skills"][agent_id]
            content = self._load_skill_content(agent_id, config, "agent_skills")
            if content:
                return LoadedSkill(
                    id=agent_id,
                    name=config.get("name", agent_id),
                    content=content,
                    priority=config.get("priority", 50),
                    tokens_used=config.get("token_budget", 500),
                    source="agent"
                )
        return None

    def create_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        triggers: List[str],
        content: str,
        skill_type: str = "domain_skills",
        priority: int = 50,
        token_budget: int = 500
    ) -> bool:
        """Create a new skill"""
        if skill_type not in self.index:
            self.index[skill_type] = {}

        self.index[skill_type][skill_id] = {
            "name": name,
            "description": description,
            "triggers": triggers,
            "priority": priority,
            "token_budget": token_budget,
            "skill_file": f"skills/{skill_id}.md"
        }

        # Write content file
        skill_file = self.skills_dir / f"{skill_id}.md"
        skill_file.write_text(f"# {name}\n\n{content}")

        self._save_index()
        return True

    def update_skill(self, skill_id: str, updates: dict) -> bool:
        """Update an existing skill"""
        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            if skill_id in self.index.get(skill_type, {}):
                self.index[skill_type][skill_id].update(updates)
                self._save_index()
                return True
        return False

    def delete_skill(self, skill_id: str) -> bool:
        """Delete a skill"""
        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            if skill_id in self.index.get(skill_type, {}):
                del self.index[skill_type][skill_id]
                self._save_index()
                return True
        return False

    def list_skills(self) -> Dict[str, List[dict]]:
        """List all skills"""
        result = {}
        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            result[skill_type] = []
            for skill_id, config in self.index.get(skill_type, {}).items():
                result[skill_type].append({
                    "id": skill_id,
                    "name": config.get("name", skill_id),
                    "description": config.get("description", ""),
                    "triggers": config.get("triggers", []),
                    "priority": config.get("priority", 50),
                    "token_budget": config.get("token_budget", 500)
                })
        return result

    def get_skill_info(self, skill_id: str) -> Optional[dict]:
        """Get detailed info about a specific skill"""
        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            if skill_id in self.index.get(skill_type, {}):
                config = self.index[skill_type][skill_id].copy()
                config["id"] = skill_id
                config["type"] = skill_type
                return config
        return None

    def search_skills(self, query: str) -> List[dict]:
        """Search for skills matching a query"""
        query_lower = query.lower()
        results = []

        for skill_type in ["agent_skills", "domain_skills", "workflow_skills"]:
            for skill_id, config in self.index.get(skill_type, {}).items():
                # Search in name, description, and triggers
                searchable = f"{config.get('name', '')} {config.get('description', '')} {' '.join(config.get('triggers', []))}"
                if query_lower in searchable.lower():
                    results.append({
                        "id": skill_id,
                        "name": config.get("name", skill_id),
                        "type": skill_type,
                        "priority": config.get("priority", 50)
                    })

        results.sort(key=lambda x: x["priority"], reverse=True)
        return results
