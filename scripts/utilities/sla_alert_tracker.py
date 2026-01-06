#!/usr/bin/env python3
"""
SLA Alert Tracker - Prevents duplicate SLA alerts from being posted to Slack

This module provides deduplication logic to ensure that:
1. The same SLA violation is not alerted more than once per 24 hours
2. Alerts are re-sent if escalation level increases
3. All alert history is tracked for audit purposes
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


DB_PATH = Path(".claude/data/bot-state/slack_state.db")


def init_sla_alerts_table():
    """Initialize the sla_alerts table if it doesn't exist"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sla_alerts (
                violation_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                last_alerted_at TIMESTAMP NOT NULL,
                alert_count INTEGER DEFAULT 1,
                current_escalation_level INTEGER DEFAULT 1,
                slack_thread_ts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for faster lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_item_id_type
            ON sla_alerts(item_id, violation_type)
        """)

    print(f"✅ SLA alerts table initialized at {DB_PATH}")


def should_alert_violation(violation: Dict[str, Any]) -> bool:
    """
    Determine if we should alert about this violation.

    Returns True if:
    - This is a new violation (never alerted before), OR
    - Last alert was more than 24 hours ago, OR
    - Escalation level has increased since last alert

    Args:
        violation: Dict with keys:
            - item_id: str (e.g., "PR-114", "ECD-123")
            - type: str (e.g., "pr_stale", "comment_response")
            - escalation_level: int (1-4)

    Returns:
        bool: True if we should send an alert
    """
    violation_id = f"{violation['item_id']}_{violation['type']}"
    item_id = violation['item_id']
    violation_type = violation['type']
    current_escalation = violation.get('escalation_level', 1)

    # Initialize table if needed
    init_sla_alerts_table()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT last_alerted_at, current_escalation_level
            FROM sla_alerts
            WHERE violation_id = ?
            """,
            (violation_id,)
        )
        result = cursor.fetchone()

        if not result:
            # New violation - should alert
            print(f"   🆕 New violation: {violation_id} - WILL ALERT")
            return True

        last_alerted_str, last_escalation = result
        last_alerted = datetime.fromisoformat(last_alerted_str)
        hours_since_alert = (datetime.now() - last_alerted).total_seconds() / 3600

        # Check if escalation level increased
        if current_escalation > last_escalation:
            print(f"   ⬆️  Escalation increased for {violation_id}: L{last_escalation} → L{current_escalation} - WILL ALERT")
            return True

        # Check if 24 hours have passed
        if hours_since_alert >= 24:
            print(f"   🕐 24+ hours since last alert for {violation_id} ({hours_since_alert:.1f}h) - WILL ALERT")
            return True

        # Otherwise, skip (recently alerted)
        print(f"   ⏭️  Skipping {violation_id}: alerted {hours_since_alert:.1f}h ago (< 24h)")
        return False


def record_alert(violation: Dict[str, Any], slack_thread_ts: Optional[str] = None):
    """
    Record that we sent an alert for this violation.

    Args:
        violation: Dict with keys:
            - item_id: str
            - type: str
            - escalation_level: int (1-4)
        slack_thread_ts: Optional thread timestamp from Slack response
    """
    violation_id = f"{violation['item_id']}_{violation['type']}"
    item_id = violation['item_id']
    violation_type = violation['type']
    current_escalation = violation.get('escalation_level', 1)
    now = datetime.now().isoformat()

    # Initialize table if needed
    init_sla_alerts_table()

    with sqlite3.connect(DB_PATH) as conn:
        # Check if violation already exists
        cursor = conn.execute(
            "SELECT alert_count FROM sla_alerts WHERE violation_id = ?",
            (violation_id,)
        )
        result = cursor.fetchone()

        if result:
            # Update existing violation
            alert_count = result[0] + 1
            conn.execute(
                """
                UPDATE sla_alerts
                SET last_alerted_at = ?,
                    alert_count = ?,
                    current_escalation_level = ?,
                    slack_thread_ts = COALESCE(?, slack_thread_ts)
                WHERE violation_id = ?
                """,
                (now, alert_count, current_escalation, slack_thread_ts, violation_id)
            )
            print(f"   💾 Updated alert record for {violation_id} (count: {alert_count})")
        else:
            # Insert new violation
            conn.execute(
                """
                INSERT INTO sla_alerts
                (violation_id, item_id, violation_type, last_alerted_at,
                 alert_count, current_escalation_level, slack_thread_ts)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (violation_id, item_id, violation_type, now, current_escalation, slack_thread_ts)
            )
            print(f"   💾 Created alert record for {violation_id}")


def get_alert_history(item_id: str, violation_type: Optional[str] = None) -> list:
    """
    Get alert history for a specific item.

    Args:
        item_id: The item ID (e.g., "PR-114")
        violation_type: Optional filter by violation type

    Returns:
        List of alert records
    """
    init_sla_alerts_table()

    with sqlite3.connect(DB_PATH) as conn:
        if violation_type:
            cursor = conn.execute(
                """
                SELECT violation_id, item_id, violation_type, last_alerted_at,
                       alert_count, current_escalation_level, slack_thread_ts
                FROM sla_alerts
                WHERE item_id = ? AND violation_type = ?
                ORDER BY last_alerted_at DESC
                """,
                (item_id, violation_type)
            )
        else:
            cursor = conn.execute(
                """
                SELECT violation_id, item_id, violation_type, last_alerted_at,
                       alert_count, current_escalation_level, slack_thread_ts
                FROM sla_alerts
                WHERE item_id = ?
                ORDER BY last_alerted_at DESC
                """,
                (item_id,)
            )

        rows = cursor.fetchall()
        return [
            {
                "violation_id": row[0],
                "item_id": row[1],
                "violation_type": row[2],
                "last_alerted_at": row[3],
                "alert_count": row[4],
                "current_escalation_level": row[5],
                "slack_thread_ts": row[6]
            }
            for row in rows
        ]


def clear_resolved_violations(item_ids: list):
    """
    Remove alerts for violations that have been resolved.
    Call this when an item is confirmed to no longer be in violation.

    Args:
        item_ids: List of item IDs that are no longer in violation
    """
    if not item_ids:
        return

    init_sla_alerts_table()

    with sqlite3.connect(DB_PATH) as conn:
        placeholders = ",".join("?" * len(item_ids))
        conn.execute(
            f"DELETE FROM sla_alerts WHERE item_id IN ({placeholders})",
            item_ids
        )

    print(f"   🧹 Cleared {len(item_ids)} resolved violations from alert tracker")


if __name__ == "__main__":
    # Initialize table when run directly
    print("Initializing SLA alerts table...")
    init_sla_alerts_table()
    print("✅ Done!")
