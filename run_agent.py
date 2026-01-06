#!/usr/bin/env python3
"""
ABOUTME: CiteMed Project Manager - Autonomous Agent Entrypoint
ABOUTME: Executes PM workflows including standup, SLA monitoring, and productivity audits

Usage:
    python run_agent.py standup           # Run daily standup workflow
    python run_agent.py sla-check         # Run SLA compliance check
    python run_agent.py --help            # Show usage information
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup_environment():
    """Ensure environment is properly configured."""
    # Note: Jira/Confluence access is via MCP connections (.mcp.json)
    # OAuth tokens are only needed for Bitbucket API if used

    # Optional: Check for Bitbucket OAuth if needed
    # For now, MCP connections handle Atlassian access
    pass


def run_standup_workflow(args):
    """
    Execute the complete 5-part standup workflow.

    Workflow:
    1. Sprint burndown analysis
    2. Code-ticket gap detection
    3. Developer productivity audit
    4. Team timesheet analysis
    5. SLA violations & follow-up tracking
    """
    import subprocess

    script_path = PROJECT_ROOT / "scripts" / "standup_workflow.py"

    cmd = ["python", str(script_path)]

    if args.dry_run:
        cmd.append("--dry-run")

    if args.verbose:
        cmd.append("--verbose")

    if args.date:
        cmd.extend(["--date", args.date])

    if args.verbose:
        print(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print(f"❌ Error: Standup workflow script not found at {script_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running standup workflow: {e}")
        sys.exit(1)


def run_sla_check(args):
    """
    Execute SLA compliance monitoring.

    Checks:
    - Jira comment response times
    - PR review turnaround
    - Blocked ticket updates
    - Stale PRs
    - Pending approval duration
    """
    import subprocess

    script_path = PROJECT_ROOT / "scripts" / "sla_check_working.py"

    cmd = ["python", str(script_path)]

    if args.dry_run:
        cmd.append("--no-slack")

    if args.verbose:
        print(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print(f"❌ Error: SLA check script not found at {script_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running SLA check: {e}")
        sys.exit(1)


def main():
    """Main entrypoint for autonomous agent execution."""
    parser = argparse.ArgumentParser(
        description="CiteMed Project Manager - Autonomous Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agent.py standup           # Daily standup workflow
  python run_agent.py sla-check         # SLA compliance check

Scheduling with cron:
  # Run standup every weekday at 9am
  0 9 * * 1-5 cd /path/to/project-manager && python run_agent.py standup

  # Run SLA checks hourly during business hours
  0 9-17 * * 1-5 cd /path/to/project-manager && python run_agent.py sla-check
        """
    )

    parser.add_argument(
        "command",
        choices=["standup", "sla-check"],
        help="Workflow to execute"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run workflow without posting to Slack/Jira"
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Run workflow for specific date (YYYY-MM-DD format)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Setup environment
    if not args.dry_run:
        setup_environment()

    # Execute requested workflow
    workflows = {
        "standup": run_standup_workflow,
        "sla-check": run_sla_check,
    }

    workflow_func = workflows.get(args.command)
    if workflow_func:
        workflow_func(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
