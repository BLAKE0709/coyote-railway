"""
COYOTE V2.5 - CLI Entrypoint

Command-line interface for COYOTE agent and all subsystems.
"""

import click
from pathlib import Path
from datetime import date, timedelta
import json

from .config import Config
from .audit import AuditTrail, ActionType, TriggerType
from .autonomy import AutonomyEngine
from .outcomes import OutcomeTracker
from .router import ModelRouter
from .skills import SkillsManager
from .memory import MemoryManager
from .heartbeat import HeartbeatService


def get_config() -> Config:
    """Get configuration from environment"""
    return Config.from_env()


def get_workspace() -> Path:
    """Get workspace path"""
    return get_config().workspace_path


@click.group()
@click.version_option(version="2.5.0")
def cli():
    """COYOTE V2.5 - Swarm Orchestration Agent"""
    pass


# =============================================================================
# MAIN COMMANDS
# =============================================================================

@cli.command()
@click.argument("message")
@click.option("--agent", default="coyote", help="Requesting agent ID")
@click.option("--model", default=None, help="Force specific model (haiku/sonnet/opus)")
def process(message, agent, model):
    """Process a message through COYOTE"""
    from .agent import CoyoteAgent

    config = get_config()
    coyote = CoyoteAgent(config)

    result = coyote.process(
        message,
        trigger_type=TriggerType.MANUAL,
        requesting_agent=agent,
        force_model=model
    )

    click.echo(f"Audit ID: {result.audit_id}")
    click.echo(f"Decision: {result.decision}")
    click.echo(f"Action: {result.action_taken or 'None (awaiting approval)'}")
    click.echo(f"Model: {result.model_used}")
    click.echo(f"Cost: ${result.cost_usd:.4f}")
    if result.skills_used:
        click.echo(f"Skills: {', '.join(result.skills_used)}")
    if result.error:
        click.echo(f"Error: {result.error}")


@cli.command()
def heartbeat():
    """Run heartbeat check"""
    from .agent import CoyoteAgent

    config = get_config()
    coyote = CoyoteAgent(config)

    result = coyote.run_heartbeat()
    click.echo(f"Heartbeat complete. Audit ID: {result.audit_id}")
    click.echo(f"Status: {'OK' if result.success else 'Issues detected'}")


@cli.command()
def status():
    """Show current COYOTE status"""
    from .agent import CoyoteAgent

    config = get_config()
    coyote = CoyoteAgent(config)

    status = coyote.get_status()
    click.echo("COYOTE V2.5 Status")
    click.echo("=" * 40)
    click.echo(f"Config Valid: {status['config_valid']}")
    click.echo(f"\nIntegrations:")
    for name, active in status['integrations'].items():
        icon = "[OK]" if active else "[--]"
        click.echo(f"  {icon} {name}")
    click.echo(f"\nPending Approvals: {status['pending_approvals']}")
    click.echo(f"Budget Used Today: ${status['budget_status']['spent']:.2f}")


# =============================================================================
# AUDIT COMMANDS
# =============================================================================

@cli.group()
def audit():
    """Audit trail commands"""
    pass


@audit.command("list")
@click.option("--days", default=7, help="Number of days to show")
@click.option("--agent", default=None, help="Filter by agent")
@click.option("--action", default=None, help="Filter by action type")
@click.option("--limit", default=50, help="Max entries to show")
def audit_list(days, agent, action, limit):
    """List recent audit entries"""
    trail = AuditTrail(get_workspace())

    action_type = ActionType(action) if action else None
    entries = trail.query(
        start_date=date.today() - timedelta(days=days),
        agent_id=agent,
        action_type=action_type,
        limit=limit
    )

    click.echo(f"Audit entries (last {days} days):")
    click.echo("-" * 80)
    for entry in entries:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M")
        click.echo(f"{ts} | {entry.agent_id:10} | {entry.action_type.value:15} | {entry.decision[:40]}")


@audit.command("stats")
@click.option("--days", default=7, help="Number of days to analyze")
def audit_stats(days):
    """Show audit statistics"""
    trail = AuditTrail(get_workspace())
    stats = trail.get_stats(days)

    click.echo(f"Audit Statistics ({days} days)")
    click.echo("=" * 40)
    click.echo(f"Total actions: {stats['total_actions']}")
    click.echo(f"Success rate: {stats['success_rate']:.1%}")
    click.echo(f"Total cost: ${stats['total_cost_usd']:.2f}")
    click.echo(f"Total tokens: {stats['total_tokens']:,}")
    click.echo(f"\nBy agent:")
    for agent, count in stats['by_agent'].items():
        click.echo(f"  {agent}: {count}")
    click.echo(f"\nBy action type:")
    for action, count in stats['by_action_type'].items():
        click.echo(f"  {action}: {count}")


@audit.command("show")
@click.argument("audit_id")
def audit_show(audit_id):
    """Show details of a specific audit entry"""
    trail = AuditTrail(get_workspace())
    entries = trail.query(limit=10000)

    for entry in entries:
        if entry.id == audit_id or entry.id.startswith(audit_id):
            click.echo(json.dumps(entry.to_dict(), indent=2))
            return

    click.echo(f"Audit entry {audit_id} not found")


# =============================================================================
# SKILLS COMMANDS
# =============================================================================

@cli.group()
def skills():
    """Skills management commands"""
    pass


@skills.command("list")
def skills_list():
    """List all available skills"""
    manager = SkillsManager(get_workspace())
    all_skills = manager.list_skills()

    for skill_type, skills in all_skills.items():
        if skills:
            click.echo(f"\n{skill_type.upper().replace('_', ' ')}:")
            for skill in skills:
                click.echo(f"  [{skill['priority']:2d}] {skill['id']}: {skill['name']}")
                triggers = ', '.join(skill['triggers'][:3])
                if len(skill['triggers']) > 3:
                    triggers += "..."
                click.echo(f"       Triggers: {triggers}")


@skills.command("test")
@click.argument("context")
def skills_test(context):
    """Test which skills would be loaded for a context"""
    manager = SkillsManager(get_workspace())
    skill_ids = manager.detect_relevant_skills(context)

    click.echo(f"Detected skills for: '{context}'")
    for sid in skill_ids:
        info = manager.get_skill_info(sid)
        if info:
            click.echo(f"  - {sid} ({info['name']})")


@skills.command("info")
@click.argument("skill_id")
def skills_info(skill_id):
    """Show details of a specific skill"""
    manager = SkillsManager(get_workspace())
    info = manager.get_skill_info(skill_id)

    if info:
        click.echo(json.dumps(info, indent=2))
    else:
        click.echo(f"Skill '{skill_id}' not found")


@skills.command("create")
@click.argument("skill_id")
@click.option("--name", required=True, help="Skill display name")
@click.option("--description", required=True, help="Skill description")
@click.option("--triggers", required=True, help="Comma-separated trigger words")
@click.option("--priority", default=50, help="Priority (1-100)")
def skills_create(skill_id, name, description, triggers, priority):
    """Create a new skill"""
    manager = SkillsManager(get_workspace())

    trigger_list = [t.strip() for t in triggers.split(",")]
    content = f"{description}\n\n[Add skill content here]"

    manager.create_skill(
        skill_id=skill_id,
        name=name,
        description=description,
        triggers=trigger_list,
        content=content,
        priority=priority
    )

    click.echo(f"Created skill: {skill_id}")
    click.echo(f"Edit content at: workspace/skills/{skill_id}.md")


# =============================================================================
# COSTS COMMANDS
# =============================================================================

@cli.group()
def costs():
    """Cost tracking commands"""
    pass


@costs.command("today")
def costs_today():
    """Show today's costs"""
    router = ModelRouter(get_workspace())
    status = router.get_today_status()

    click.echo(f"Today's Costs ({status['date']})")
    click.echo("=" * 40)
    click.echo(f"Spent: ${status['spent']:.2f}")
    click.echo(f"Limit: ${status['limit']:.2f}")
    click.echo(f"Remaining: ${status['remaining']:.2f}")
    click.echo(f"Usage: {status['percent_used']:.1f}%")
    click.echo(f"\nBy model:")
    for model, cost in status['by_model'].items():
        click.echo(f"  {model}: ${cost:.2f}")
    click.echo(f"\nBy agent:")
    for agent, cost in status['by_agent'].items():
        click.echo(f"  {agent}: ${cost:.2f}")


@costs.command("week")
def costs_week():
    """Show this week's costs"""
    router = ModelRouter(get_workspace())
    summary = router.get_cost_summary(days=7)

    click.echo(f"7-Day Cost Summary")
    click.echo("=" * 40)
    click.echo(f"Total: ${summary['total_cost']:.2f}")
    click.echo(f"Daily average: ${summary['daily_average']:.2f}")
    click.echo(f"\nBy day:")
    for day, cost in sorted(summary['by_day'].items(), reverse=True):
        click.echo(f"  {day}: ${cost:.2f}")
    click.echo(f"\nBy model:")
    for model, cost in summary['by_model'].items():
        click.echo(f"  {model}: ${cost:.2f}")


@costs.command("agent")
@click.argument("agent_id")
def costs_agent(agent_id):
    """Show budget status for a specific agent"""
    router = ModelRouter(get_workspace())
    status = router.get_agent_budget_status(agent_id)

    click.echo(f"Budget Status: {agent_id}")
    click.echo("=" * 40)
    click.echo(f"Spent: ${status['spent']:.2f}")
    click.echo(f"Limit: ${status['limit']:.2f}")
    click.echo(f"Remaining: ${status['remaining']:.2f}")
    click.echo(f"Usage: {status['percent_used']:.1f}%")


# =============================================================================
# OUTCOMES COMMANDS
# =============================================================================

@cli.group()
def outcomes():
    """Outcome tracking commands"""
    pass


@outcomes.command("report")
@click.option("--agent", default=None, help="Filter by agent")
@click.option("--days", default=30, help="Number of days to analyze")
def outcomes_report(agent, days):
    """Show effectiveness report"""
    trail = AuditTrail(get_workspace())
    tracker = OutcomeTracker(get_workspace(), trail)

    report = tracker.get_effectiveness_report(agent, days)

    click.echo(f"Effectiveness Report ({days} days)")
    click.echo("=" * 40)
    click.echo(f"Total actions: {report['total_actions']}")
    click.echo(f"Outcomes tracked: {report.get('outcomes_tracked', 0)}")
    click.echo(f"Tracking rate: {report.get('tracking_rate', 0):.1%}")
    click.echo(f"Value generated: ${report.get('value_generated_usd', 0):.2f}")

    if report.get('by_action_type'):
        click.echo(f"\nBy action type:")
        for action, stats in report['by_action_type'].items():
            eff = stats.get('effectiveness', 0)
            click.echo(f"  {action}: {eff:.0%} effective ({stats['acted_on']}/{stats['total']})")

    if report.get('recommendations'):
        click.echo(f"\nRecommendations:")
        for rec in report['recommendations']:
            click.echo(f"  - {rec}")


@outcomes.command("pending")
def outcomes_pending():
    """Show actions awaiting outcome tracking"""
    trail = AuditTrail(get_workspace())
    pending = trail.get_pending_outcomes()

    click.echo(f"Pending Outcomes: {len(pending)}")
    click.echo("-" * 60)
    for item in pending[:20]:
        click.echo(f"  {item['timestamp'][:10]} | {item['agent_id']:10} | {item['action_type']}")


@outcomes.command("check")
def outcomes_check():
    """Run outcome detection"""
    trail = AuditTrail(get_workspace())
    tracker = OutcomeTracker(get_workspace(), trail)

    updated = tracker.check_pending_outcomes()
    click.echo(f"Checked pending outcomes. Updated: {updated}")


# =============================================================================
# AUTONOMY COMMANDS
# =============================================================================

@cli.group()
def autonomy():
    """Autonomy and approval commands"""
    pass


@autonomy.command("pending")
def autonomy_pending():
    """Show pending approval requests"""
    engine = AutonomyEngine(get_workspace())
    pending = engine.get_pending_approvals()

    click.echo(f"Pending Approvals: {len(pending)}")
    click.echo("-" * 60)
    for approval in pending:
        click.echo(f"\nRequest ID: {approval['request_id']}")
        click.echo(f"Agent: {approval['agent_id']}")
        click.echo(f"Action: {approval['action']}")
        click.echo(f"Requested: {approval['requested_at']}")


@autonomy.command("approve")
@click.argument("request_id")
def autonomy_approve(request_id):
    """Approve a pending request"""
    engine = AutonomyEngine(get_workspace())

    if engine.approve_request(request_id):
        click.echo(f"Approved request: {request_id}")
    else:
        click.echo(f"Request not found: {request_id}")


@autonomy.command("reject")
@click.argument("request_id")
@click.option("--reason", default="", help="Rejection reason")
def autonomy_reject(request_id, reason):
    """Reject a pending request"""
    engine = AutonomyEngine(get_workspace())

    if engine.reject_request(request_id, reason=reason):
        click.echo(f"Rejected request: {request_id}")
    else:
        click.echo(f"Request not found: {request_id}")


@autonomy.command("check")
@click.argument("agent_id")
@click.argument("action_category")
@click.argument("action_type")
def autonomy_check(agent_id, action_category, action_type):
    """Check if an action is permitted"""
    engine = AutonomyEngine(get_workspace())

    result = engine.check_permission(
        agent_id=agent_id,
        action_category=action_category,
        action_type=action_type,
        context={}
    )

    click.echo(f"Permission Check: {agent_id} -> {action_category}.{action_type}")
    click.echo(f"Allowed: {result.allowed}")
    click.echo(f"Level: {result.level.value}")
    click.echo(f"Reason: {result.reason}")


# =============================================================================
# MEMORY COMMANDS
# =============================================================================

@cli.group()
def memory():
    """Memory management commands"""
    pass


@memory.command("search")
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
def memory_search(query, limit):
    """Search memories"""
    manager = MemoryManager(get_workspace())
    results = manager.search(query, limit=limit)

    click.echo(f"Found {len(results)} memories:")
    for mem in results:
        click.echo(f"\n[{mem.id}] {mem.category} (importance: {mem.importance})")
        click.echo(f"  {mem.content[:100]}")


@memory.command("add")
@click.argument("content")
@click.option("--category", default="general", help="Memory category")
@click.option("--importance", default=5, help="Importance (1-10)")
@click.option("--tags", default="", help="Comma-separated tags")
def memory_add(content, category, importance, tags):
    """Add a new memory"""
    manager = MemoryManager(get_workspace())

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    mem = manager.add(
        content=content,
        category=category,
        importance=importance,
        tags=tag_list
    )

    click.echo(f"Added memory: {mem.id}")


@memory.command("stats")
def memory_stats():
    """Show memory statistics"""
    manager = MemoryManager(get_workspace())
    stats = manager.get_stats()

    click.echo("Memory Statistics")
    click.echo("=" * 40)
    click.echo(f"Total memories: {stats['total_memories']}")
    click.echo(f"\nBy category:")
    for cat, count in stats['by_category'].items():
        click.echo(f"  {cat}: {count}")


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
