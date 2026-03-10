"""
System / project configuration helper.

Resolves project settings from the DB (system_config table, managed via the
dashboard Settings → Project Settings UI), with optional ENV var fallback.

Priority: DB value > ENV fallback > None

Usage:
    from src.utils.system_config import get_setting, get_all_settings

    cloud_id = get_setting("atlassian_cloud_id", env_fallback="ATLASSIAN_CLOUD_ID")
    workspace = get_setting("bitbucket_workspace", env_fallback="BITBUCKET_WORKSPACE")

Settings keys (kept in sync with PROJECT_SETTINGS in app.py):
    atlassian_cloud_id    - Atlassian Cloud UUID
    jira_url              - Jira instance URL (e.g. https://company.atlassian.net)
    jira_project_key      - Primary Jira project key (e.g. ECD)
    bitbucket_workspace   - Bitbucket workspace slug (e.g. mycompany)
    confluence_spaces     - Comma-separated Confluence space keys (e.g. ENG,DOCS)
"""

import os
from typing import Optional


def get_setting(key: str, env_fallback: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """
    Return the value for *key* from the system_config DB table.

    Falls back to the named ENV var if the DB has no value, then to *default*.
    Returns None if nothing is configured.
    """
    try:
        from src.database.connection import get_engine
        from sqlalchemy import text

        engine = get_engine(default_path=".claude/data/bot-state/dashboard.db")
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM system_config WHERE key = :k"),
                {"k": key},
            ).first()
            if row and row[0]:
                return row[0]
    except Exception:
        pass

    # Fall back to ENV var
    if env_fallback:
        val = os.getenv(env_fallback)
        if val:
            return val

    return default


def get_all_settings() -> dict:
    """
    Return all system_config rows as a {key: value} dict.
    Used by the dashboard API to show current values.
    """
    try:
        from src.database.connection import get_engine
        from sqlalchemy import text

        engine = get_engine(default_path=".claude/data/bot-state/dashboard.db")
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT key, value FROM system_config")
            ).fetchall()
            return {row[0]: row[1] for row in rows if row[1]}
    except Exception:
        return {}


def save_setting(key: str, value: Optional[str]) -> None:
    """
    Upsert a single setting into system_config.
    Called by the dashboard API on save.
    """
    from src.database.connection import get_engine
    from sqlalchemy import text
    from datetime import datetime

    engine = get_engine(default_path=".claude/data/bot-state/dashboard.db")
    now = datetime.utcnow()

    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM system_config WHERE key = :k"),
            {"k": key},
        ).first()

        if existing:
            conn.execute(
                text("UPDATE system_config SET value = :v, updated_at = :now WHERE key = :k"),
                {"v": value or None, "now": now, "k": key},
            )
        else:
            conn.execute(
                text("INSERT INTO system_config (key, value, updated_at) VALUES (:k, :v, :now)"),
                {"k": key, "v": value or None, "now": now},
            )
