"""
COYOTE V2.5 - Swarm Orchestration Layer

Production-grade agent orchestration with:
- Unified Audit Trail
- Autonomy Rules Engine
- Outcome Tracking
- Multi-Model Routing
- Skills Framework
- Memory System
- Alert Service
- Heartbeat Monitoring
"""

__version__ = "2.5.0"

from .audit import (
    AuditTrail,
    AuditEntry,
    TriggerType,
    ActionType,
    ActionResult,
    AutonomyLevel,
    OutcomeStatus
)

from .autonomy import (
    AutonomyEngine,
    PermissionResult
)

from .outcomes import (
    OutcomeTracker,
    DetectedOutcome
)

from .router import (
    ModelRouter,
    RoutingDecision,
    CostTracker
)

from .skills import (
    SkillsManager,
    LoadedSkill
)

from .config import Config

from .memory import (
    MemoryManager,
    Memory
)

from .alerts import AlertService

from .heartbeat import (
    HeartbeatService,
    HeartbeatResult,
    HeartbeatCheck
)

from .agent import (
    CoyoteAgent,
    AgentResponse
)

__all__ = [
    # Version
    "__version__",

    # Audit
    "AuditTrail",
    "AuditEntry",
    "TriggerType",
    "ActionType",
    "ActionResult",
    "AutonomyLevel",
    "OutcomeStatus",

    # Autonomy
    "AutonomyEngine",
    "PermissionResult",

    # Outcomes
    "OutcomeTracker",
    "DetectedOutcome",

    # Router
    "ModelRouter",
    "RoutingDecision",
    "CostTracker",

    # Skills
    "SkillsManager",
    "LoadedSkill",

    # Config
    "Config",

    # Memory
    "MemoryManager",
    "Memory",

    # Alerts
    "AlertService",

    # Heartbeat
    "HeartbeatService",
    "HeartbeatResult",
    "HeartbeatCheck",

    # Agent
    "CoyoteAgent",
    "AgentResponse",
]
