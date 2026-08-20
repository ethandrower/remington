"""Remington's PM tool surface (MCP server).

Wraps the pure `pm_core` package (extracted from the old monolith's
`scripts/core`) as MCP tools an OpenClaw agent can load. These are the tools the
routines in ROUTINES.md call: SLA sweep, blocked-ticket analysis, portfolio
audit, timesheet, daily priorities, PM self-audit, and the composite standup.

Design:
- Every tool builds a `PMConfig` from the environment (`load_config()`).
- Stateful tools (sla, blocked, portfolio, standup) accept `prior_state` and
  RETURN the new `state` in their result. The agent reads the relevant STATE.md
  block, passes it in, and writes the returned state back — nothing is persisted
  here. This replaces the monolith's SQLite alert-tracker.
- Tools COMPUTE ONLY. Posting to Slack / commenting on Jira is done by the agent
  through the trinity MCP (with the propose->approve->execute standing order).

Run (from the `openclaw/` dir, or with it on PYTHONPATH):
    python -m remington_mcp.pm_mcp    # stdio transport
Register in the gateway's OpenClaw config as an MCP server named "pm".
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .pm_core import (
    check_slas,
    analyze_blocked_tickets,
    check_portfolio_health,
    build_timesheet,
    build_daily_priorities,
    run_pm_audit,
    run_standup,
)

mcp = FastMCP("pm")


def _safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Return a structured error dict instead of raising, so the agent gets a message."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 — surface, don't crash the server
            return {"error": f"{type(e).__name__}: {e}", "type": "pm_core"}

    return wrapper


# ===========================================================================
# Stateful routines — pass prior_state in, get new state back
# ===========================================================================
@mcp.tool()
@_safe
def sla_check(prior_state: Optional[dict] = None) -> dict:
    """Sweep SLA breaches (QA stalled, Pending-Approval, Blocked, Changes-Requested).

    Pass the `sla` block from STATE.md as `prior_state` so already-alerted
    violations aren't re-flagged. Returns violations, `alerts_to_send`
    (cooldown/escalation applied), and the new `state` to write back to STATE.md.
    """
    return check_slas(load_config(), prior_state)


@mcp.tool()
@_safe
def blocked_analysis(prior_state: Optional[dict] = None) -> dict:
    """Analyze blocked tickets via the decision tree (no-link / blocker-resolved /
    cascading-block / legitimately-blocked).

    Pass the `blocked` block from STATE.md as `prior_state` for 48h dedup.
    Legitimately-blocked tickets include their recent comments for the agent to
    triage. Returns tickets, by_category, alerts_to_send, and new `state`.
    """
    return analyze_blocked_tickets(load_config(), prior_state)


@mcp.tool()
@_safe
def portfolio_audit(prior_state: Optional[dict] = None) -> dict:
    """Run the 7 initiative/epic hygiene signals across the portfolio.

    Pass the `initiatives` block from STATE.md as `prior_state` to carry a trend.
    Returns per-initiative records, counts, and state.
    """
    return check_portfolio_health(load_config(), prior_state)


@mcp.tool()
@_safe
def standup(prior_state: Optional[dict] = None) -> dict:
    """Run the composite daily standup (burndown, code<->ticket gaps, productivity,
    timesheet glance, SLA roll-up, deadline risk, DoR enforcement).

    Pass the full STATE.md (at least the `sla` block) as `prior_state`. Returns
    per-section results, alerts_to_send, suggested DoR comment texts, and new state.
    """
    return run_standup(load_config(), prior_state)


# ===========================================================================
# Stateless / input-driven routines
# ===========================================================================
@mcp.tool()
@_safe
def timesheet(week_offset: int = 0, current_week: bool = False) -> dict:
    """Build the weekly timesheet/worklog report: hours vs estimates per developer.

    week_offset=0 is last complete week; current_week=True uses the in-progress week.
    """
    return build_timesheet(load_config(), week_offset=week_offset, current_week=current_week)


@mcp.tool()
@_safe
def daily_priorities(roster: list, violations: Optional[dict] = None) -> dict:
    """Rank each team member's tickets into a prioritized daily list.

    `roster` = list of {name, slack_id, jira_id}. `violations` (optional) keyed by
    ticket key — feed the `violations`/`state` from a prior sla_check to boost
    tickets with active SLA breaches.
    """
    return build_daily_priorities(load_config(), roster, violations)


@mcp.tool()
@_safe
def pm_audit(
    pm_account_id: str,
    pm_names: Optional[list] = None,
    sprint_id: Optional[int] = None,
    thresholds: Optional[dict] = None,
) -> dict:
    """Score the PM's OWN performance for a sprint (6 metric groups, A/B/C/D grades).

    `pm_account_id` is required (the PM's Jira accountId). Omit `sprint_id` to use
    the active sprint. Feeds the weekly self-audit / reflection.
    """
    return run_pm_audit(
        load_config(),
        pm_account_id,
        pm_names=pm_names,
        sprint_id=sprint_id,
        thresholds=thresholds,
    )


if __name__ == "__main__":
    mcp.run()
