"""pm_core — pure business logic for the PM automation routines.

Extracted from ``scripts/core/*`` and decoupled from the old monolith: no DB,
no Slack, no Flask, no service objects. All Jira data flows through the
``trinity`` package; every function COMPUTES and RETURNS JSON-serialisable
dicts/lists. Functions that need cross-run memory take a ``prior_state`` dict
and return the new state in their result (mirroring the agent's STATE.md) —
nothing is persisted here. Posting/commenting/persisting is the caller's job.

This is the layer the PM MCP server wraps.

Public API (all take a ``PMConfig`` from ``openclaw.mcp.config``):
    check_slas(cfg, prior_state)               -> sla.py
    analyze_blocked_tickets(cfg, prior_state)  -> blocked.py
    check_portfolio_health(cfg, prior_state)   -> portfolio.py
    build_timesheet(cfg, ...)                  -> timesheet.py
    build_daily_priorities(cfg, roster, ...)   -> priorities.py
    run_pm_audit(cfg, pm_account_id, ...)      -> audit.py
    run_standup(cfg, prior_state)              -> standup.py
"""

from .sla import check_slas
from .blocked import analyze_blocked_tickets
from .portfolio import check_portfolio_health
from .timesheet import build_timesheet
from .priorities import build_daily_priorities
from .audit import run_pm_audit, compute_pm_audit
from .standup import run_standup

__all__ = [
    "check_slas",
    "analyze_blocked_tickets",
    "check_portfolio_health",
    "build_timesheet",
    "build_daily_priorities",
    "run_pm_audit",
    "compute_pm_audit",
    "run_standup",
]
