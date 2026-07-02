"""Shared date / business-hours helpers for pm_core.

Every routine that does time math (SLA age, PM-audit response times, timesheet
week bounds, portfolio staleness) funnels through here so the business-hours
definition lives in exactly one place. Business hours / holidays come from the
`PMConfig` the caller passes in — nothing reads the environment directly.

Also holds one non-date helper — `jira_project_clause` — because every routine
needs to turn the configured project key(s) into a JQL clause and there is no
other shared module to hang it on.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple


# ── JQL project clause ───────────────────────────────────────────────────────

def jira_project_clause(project_key: str) -> str:
    """Turn "ECD" or "ECD,MDP" into a JQL-ready clause.

    Returns ``project = ECD`` for a single key or ``project IN (ECD, MDP)`` for
    several. Mirrors the clause-building duplicated across the old scripts.
    """
    keys = [k.strip() for k in (project_key or "").split(",") if k.strip()]
    if not keys:
        return "project = "
    if len(keys) == 1:
        return f"project = {keys[0]}"
    return f'project IN ({", ".join(keys)})'


# ── Parsing ──────────────────────────────────────────────────────────────────

def parse_jira_datetime(s: Optional[str]) -> Optional[datetime]:
    """Parse a Jira ISO timestamp (``2025-03-26T10:00:00.000+0000``) to datetime.

    Preserves timezone info when present. Returns ``None`` on empty/garbage.
    Consolidates the four near-identical ``_parse_dt`` helpers from the old
    scripts (pm_audit, daily_priorities, blocked, sla).
    """
    if not s:
        return None
    text = s.strip()
    try:
        # Fast path: fromisoformat handles most Jira strings once Z is normalised
        normalized = text.replace("Z", "+00:00")
        # Jira uses +0000 (no colon); insert a colon so fromisoformat accepts it
        if len(normalized) >= 5 and normalized[-5] in "+-" and normalized[-3] != ":":
            normalized = normalized[:-2] + ":" + normalized[-2:]
        return datetime.fromisoformat(normalized)
    except (ValueError, IndexError):
        pass
    # Fallback: strip fractional seconds + offset, parse naive
    try:
        clean = text[:-1] if text.endswith("Z") else text
        for i in range(len(clean) - 1, max(len(clean) - 7, 9), -1):
            if clean[i] in ("+", "-") and i > 10:
                clean = clean[:i]
                break
        if "." in clean[10:]:
            clean = clean[: clean.index(".", 10)]
        return datetime.fromisoformat(clean)
    except (ValueError, IndexError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ── Elapsed-time helpers ─────────────────────────────────────────────────────

def hours_since(start: Optional[datetime], now: Optional[datetime] = None) -> float:
    """Calendar hours between ``start`` and now (tz-aware safe)."""
    if not start:
        return 0.0
    ref = now or (datetime.now(start.tzinfo) if start.tzinfo else datetime.now())
    return (ref - start).total_seconds() / 3600


def simple_business_hours(start: datetime, now: Optional[datetime] = None) -> float:
    """Rough business-hours approximation: calendar hours * 40/168.

    Ported verbatim from ``sla_check_working.calculate_business_hours_simple``
    (used for PR staleness where a precise calendar is overkill).
    """
    ref = now or (datetime.now(start.tzinfo) if start.tzinfo else datetime.now())
    total_hours = (ref - start).total_seconds() / 3600
    return total_hours * 0.238


def business_hours_between(
    start: Optional[datetime],
    end: Optional[datetime],
    start_hour: int = 9,
    end_hour: int = 17,
    holidays: Iterable[str] = (),
) -> float:
    """Business hours between two datetimes, honouring a working window.

    Counts only Mon–Fri, only the ``start_hour``..``end_hour`` window each day,
    and skips any date in ``holidays`` (``YYYY-MM-DD`` strings). Ported from
    ``pm_audit_compute._business_hours_between`` and generalised to take the
    window + holidays from config.
    """
    if not start or not end or end <= start:
        return 0.0
    holiday_set = set(holidays or ())
    total = 0.0
    current = start
    while current < end:
        is_weekday = current.weekday() < 5
        is_holiday = current.strftime("%Y-%m-%d") in holiday_set
        if is_weekday and not is_holiday:
            day_start = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            day_end = current.replace(hour=end_hour, minute=0, second=0, microsecond=0)
            eff_start = max(current, day_start)
            eff_end = min(end, day_end)
            if eff_end > eff_start:
                total += (eff_end - eff_start).total_seconds() / 3600
        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return round(total, 1)


# ── Calendar-day helpers (portfolio) ─────────────────────────────────────────

def days_ago(date_str: Optional[str]) -> Optional[int]:
    """Calendar days from a ``YYYY-MM-DD``/ISO string to now (UTC)."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, IndexError):
        return None


def past_due(due: Optional[str]) -> bool:
    """True if a ``YYYY-MM-DD`` due date is strictly in the past (UTC)."""
    if not due:
        return False
    try:
        d = datetime.strptime(due[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return d < datetime.now(timezone.utc)
    except (ValueError, IndexError):
        return False


# ── Week bounds (timesheet) ──────────────────────────────────────────────────

def get_week_bounds(
    timezone_name: str,
    week_offset: int = 0,
    current_week: bool = False,
) -> Tuple[datetime, datetime]:
    """Return (week_start, week_end) as tz-aware datetimes.

    ``week_offset=0`` → last completed Mon–Sun. ``week_offset=1`` → two weeks
    ago. ``current_week`` → this Monday 00:00 → now. Ported from
    ``timesheet_report.get_week_bounds``.
    """
    import pytz

    tz = pytz.timezone(timezone_name)
    now = datetime.now(tz)
    days_since_monday = now.weekday()  # Monday = 0

    if current_week:
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = now
    else:
        last_sunday = now - timedelta(days=days_since_monday + 1)
        last_monday = last_sunday - timedelta(days=6)
        last_monday -= timedelta(weeks=week_offset)
        last_sunday -= timedelta(weeks=week_offset)
        week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return week_start, week_end
