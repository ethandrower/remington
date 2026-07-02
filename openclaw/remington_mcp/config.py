"""Shared configuration for Remington's MCP tool layer.

Both trinity_mcp and pm_mcp import from here so there is ONE place that reads the
environment. On the gateway these come from the OpenClaw process environment
(never from a committed file).

Atlassian/Bitbucket auth itself is handled entirely by the `trinity` package,
which reads ATLASSIAN_EMAIL / ATLASSIAN_API_TOKEN (and BITBUCKET_* ) from the
environment or `trinity config`. We do not duplicate credential handling here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PMConfig:
    project_key: str
    cloud_id: str
    jira_url: str
    business_start: int
    business_end: int
    timezone: str
    holidays: tuple[str, ...]

    @property
    def browse_base(self) -> str:
        return f"{self.jira_url.rstrip('/')}/browse"


def load_config() -> PMConfig:
    """Build config from the environment. Fails loud on the two required values."""
    project_key = os.environ.get("ATLASSIAN_PROJECT_KEY") or os.environ.get("PM_PROJECT_KEY")
    cloud_id = os.environ.get("ATLASSIAN_CLOUD_ID", "")
    jira_url = (
        os.environ.get("JIRA_INSTANCE_URL")
        or os.environ.get("JIRA_BASE_URL")
        or "https://citemed.atlassian.net"
    )
    if not project_key:
        raise RuntimeError(
            "ATLASSIAN_PROJECT_KEY (or PM_PROJECT_KEY) must be set for the PM MCP tools."
        )
    holidays = tuple(
        h.strip() for h in os.environ.get("COMPANY_HOLIDAYS", "").split(",") if h.strip()
    )
    return PMConfig(
        project_key=project_key,
        cloud_id=cloud_id,
        jira_url=jira_url,
        business_start=int(os.environ.get("BUSINESS_HOURS_START", "9")),
        business_end=int(os.environ.get("BUSINESS_HOURS_END", "17")),
        timezone=os.environ.get("BUSINESS_TIMEZONE", "America/New_York"),
        holidays=holidays,
    )
