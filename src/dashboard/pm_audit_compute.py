"""
PM Self-Audit Compute Layer

Pure Python module — no Flask, no Jira deps.
Takes raw data (tickets, comments, changelogs) and returns audit metrics.
Same pattern as sprint_report.py.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# ── Default grading thresholds ────────────────────────────────────────────────
# Can be overridden via system_config DB table.

DEFAULT_THRESHOLDS = {
    'approval': {
        'A': {'avg_hours': 8,  'backlog': 2},
        'B': {'avg_hours': 24, 'backlog': 5},
        'C': {'avg_hours': 48, 'backlog': 8},
    },
    'engagement': {
        'A': {'ratio': 0.80},
        'B': {'ratio': 0.60},
        'C': {'ratio': 0.40},
    },
    'responsiveness': {
        'A': {'avg_hours': 4,  'waiting': 2},
        'B': {'avg_hours': 12, 'waiting': 5},
        'C': {'avg_hours': 24, 'waiting': 8},
    },
    'grooming': {
        'A': {'estimation_pct': 90},
        'B': {'estimation_pct': 75},
        'C': {'estimation_pct': 50},
    },
    'transitions': {
        'A': {'min_transitions': 20, 'min_reopens': 3},
        'B': {'min_transitions': 10, 'min_reopens': 1},
        'C': {'min_transitions': 5,  'min_reopens': 0},
    },
    'blocker_response': {
        'A': {'avg_hours': 4,  'no_engagement': 0},
        'B': {'avg_hours': 12, 'no_engagement': 1},
        'C': {'avg_hours': 24, 'no_engagement': 3},
    },
}

GRADE_WEIGHTS = {
    'approval': 0.25,
    'engagement': 0.20,
    'responsiveness': 0.20,
    'grooming': 0.10,
    'transitions': 0.10,
    'blocker_response': 0.15,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string (with or without timezone).
    Handles Jira format: 2025-03-26T10:00:00.000+0000
    """
    if not s:
        return None
    try:
        # Strip timezone suffix for naive comparison
        clean = s
        # Remove Z
        if clean.endswith('Z'):
            clean = clean[:-1]
        # Remove +0000, +00:00, -0500, -05:00 style offsets
        for i in range(len(clean) - 1, max(len(clean) - 7, 9), -1):
            if clean[i] in ('+', '-') and i > 10:
                clean = clean[:i]
                break
        # Remove fractional seconds (.000, .123456)
        if '.' in clean[10:]:
            clean = clean[:clean.index('.', 10)]
        return datetime.fromisoformat(clean)
    except (ValueError, IndexError):
        return None


def _business_hours_between(start: datetime, end: datetime) -> float:
    """Rough business hours between two datetimes (8h/weekday)."""
    if not start or not end or end <= start:
        return 0.0
    total_hours = 0.0
    current = start
    while current < end:
        if current.weekday() < 5:  # Mon-Fri
            day_start = current.replace(hour=9, minute=0, second=0)
            day_end = current.replace(hour=17, minute=0, second=0)
            effective_start = max(current, day_start)
            effective_end = min(end, day_end)
            if effective_end > effective_start:
                total_hours += (effective_end - effective_start).total_seconds() / 3600
        current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    return round(total_hours, 1)


def _pm_matches(author_id: Optional[str], author_name: Optional[str],
                pm_account_id: str, pm_names: List[str]) -> bool:
    """Check if author matches PM by account ID or display name."""
    if author_id and author_id == pm_account_id:
        return True
    if author_name:
        name_lower = author_name.lower()
        for n in pm_names:
            if n.lower() == name_lower:
                return True
    return False


# ── Metric Group Computers ────────────────────────────────────────────────────

def _compute_approval_velocity(
    tickets: List[Dict],
    changelogs: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: List[str],
) -> Dict[str, Any]:
    """
    A. Approval Velocity
    - Avg time in Pending Approval
    - Current backlog
    - Approvals completed by PM
    """
    approval_durations = []  # hours each ticket spent in Pending Approval
    current_backlog = []
    approvals_completed = 0
    detail = []

    for ticket in tickets:
        key = ticket.get('key', '')
        status = ticket.get('status', '')
        entries = changelogs.get(key, [])

        # Track time in Pending Approval from changelog
        entered_pa = None
        ticket_pa_hours = 0.0

        for entry in entries:
            for item in entry.get('items', []):
                if item.get('field') != 'status':
                    continue
                to_str = (item.get('toString') or '').strip()
                from_str = (item.get('fromString') or '').strip()
                ts = _parse_dt(entry.get('created'))

                if to_str == 'Pending Approval' and entered_pa is None:
                    entered_pa = ts
                elif from_str == 'Pending Approval' and entered_pa and ts:
                    hours = _business_hours_between(entered_pa, ts)
                    ticket_pa_hours += hours
                    approval_durations.append(hours)

                    # Check if PM did the transition
                    author_id = entry.get('author', {}).get('accountId')
                    author_name = entry.get('author', {}).get('displayName')
                    if _pm_matches(author_id, author_name, pm_account_id, pm_names):
                        approvals_completed += 1

                    entered_pa = None

        # Still in Pending Approval?
        if status == 'Pending Approval':
            current_backlog.append(key)
            if entered_pa:
                hours = _business_hours_between(entered_pa, datetime.utcnow())
                ticket_pa_hours += hours
                approval_durations.append(hours)

        if ticket_pa_hours > 0 or status == 'Pending Approval':
            detail.append({
                'key': key,
                'summary': ticket.get('summary', ''),
                'pa_hours': round(ticket_pa_hours, 1),
                'currently_pending': status == 'Pending Approval',
            })

    avg_hours = round(sum(approval_durations) / len(approval_durations), 1) if approval_durations else 0.0

    return {
        'avg_pending_approval_hours': avg_hours,
        'pending_approval_backlog': len(current_backlog),
        'approvals_completed': approvals_completed,
        'detail': sorted(detail, key=lambda d: d['pa_hours'], reverse=True),
    }


def _compute_comment_activity(
    tickets: List[Dict],
    comments: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: List[str],
) -> Dict[str, Any]:
    """
    B. Comment Activity & Responsiveness
    - Total PM comments, engagement ratio
    - Threads waiting on PM, avg response time
    """
    total_pm_comments = 0
    tickets_with_pm_comment = set()
    threads_waiting = []
    response_times = []
    detail = []

    for ticket in tickets:
        key = ticket.get('key', '')
        ticket_comments = comments.get(key, [])
        if not ticket_comments:
            continue

        pm_comment_count = 0
        pm_commented = False
        last_pm_comment_time = None

        # Sort by created time
        sorted_comments = sorted(ticket_comments, key=lambda c: c.get('created', ''))

        # Track response times: non-PM comment → next PM comment
        pending_non_pm = None

        for c in sorted_comments:
            author_id = c.get('author', {}).get('accountId')
            author_name = c.get('author', {}).get('displayName')
            created = _parse_dt(c.get('created'))
            is_pm = _pm_matches(author_id, author_name, pm_account_id, pm_names)

            if is_pm:
                pm_comment_count += 1
                pm_commented = True
                last_pm_comment_time = created
                if pending_non_pm and created:
                    hours = _business_hours_between(pending_non_pm, created)
                    response_times.append(hours)
                    pending_non_pm = None
            else:
                if pm_commented and created:
                    # PM previously engaged — a non-PM comment starts a response clock
                    pending_non_pm = created

        total_pm_comments += pm_comment_count
        if pm_commented:
            tickets_with_pm_comment.add(key)

        # Is PM the last commenter? If not, and PM engaged before, it's waiting
        if sorted_comments:
            last_c = sorted_comments[-1]
            last_author_id = last_c.get('author', {}).get('accountId')
            last_author_name = last_c.get('author', {}).get('displayName')
            if pm_commented and not _pm_matches(last_author_id, last_author_name, pm_account_id, pm_names):
                threads_waiting.append(key)

        detail.append({
            'key': key,
            'summary': ticket.get('summary', ''),
            'pm_comments': pm_comment_count,
            'total_comments': len(ticket_comments),
            'waiting_on_pm': key in threads_waiting,
            'last_commenter': sorted_comments[-1].get('author', {}).get('displayName', '') if sorted_comments else '',
        })

    total_tickets = len(tickets)
    engagement_ratio = round(len(tickets_with_pm_comment) / total_tickets, 2) if total_tickets > 0 else 0.0
    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0.0

    return {
        'total_pm_comments': total_pm_comments,
        'tickets_engaged': len(tickets_with_pm_comment),
        'total_sprint_tickets': total_tickets,
        'engagement_ratio': engagement_ratio,
        'threads_waiting_on_pm': len(threads_waiting),
        'avg_pm_response_hours': avg_response,
        'detail': sorted(detail, key=lambda d: d['pm_comments'], reverse=True),
    }


def _compute_grooming(
    tickets: List[Dict],
    pm_account_id: str,
) -> Dict[str, Any]:
    """
    C. Ticket Creation & Grooming
    - Tickets created by PM, estimation coverage
    """
    created_by_pm = []
    estimated = 0
    unestimated = []

    for ticket in tickets:
        key = ticket.get('key', '')
        reporter_id = ticket.get('reporter_id', '')

        if reporter_id == pm_account_id:
            created_by_pm.append(key)

        if ticket.get('original_estimate_seconds') and ticket['original_estimate_seconds'] > 0:
            estimated += 1
        else:
            unestimated.append({
                'key': key,
                'summary': ticket.get('summary', ''),
                'assignee': ticket.get('assignee', ''),
                'status': ticket.get('status', ''),
            })

    total = len(tickets)
    coverage = round(estimated / total * 100, 1) if total > 0 else 0.0

    return {
        'tickets_created_by_pm': len(created_by_pm),
        'estimation_coverage_pct': coverage,
        'unestimated_count': len(unestimated),
        'detail': {
            'created_tickets': created_by_pm,
            'unestimated_tickets': unestimated,
        },
    }


def _compute_transitions(
    changelogs: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: List[str],
) -> Dict[str, Any]:
    """
    D. Status Transition Activity
    - Transitions by PM, reopens/rejections, breakdown
    """
    BACKWARD_STATUSES = {
        'To Do', 'Open', 'Ready For Development', 'In Development', 'In Progress',
    }
    FORWARD_STATUSES = {
        'Done', 'Closed', 'Ready For QA', 'Pending Approval', 'Complete',
    }

    pm_transitions = 0
    reopens = 0
    breakdown = {}
    detail = []

    for key, entries in changelogs.items():
        for entry in entries:
            author_id = entry.get('author', {}).get('accountId')
            author_name = entry.get('author', {}).get('displayName')
            if not _pm_matches(author_id, author_name, pm_account_id, pm_names):
                continue

            for item in entry.get('items', []):
                if item.get('field') != 'status':
                    continue
                from_str = (item.get('fromString') or '').strip()
                to_str = (item.get('toString') or '').strip()
                pm_transitions += 1

                label = f"{from_str} -> {to_str}"
                breakdown[label] = breakdown.get(label, 0) + 1

                # Reopen/rejection: moving from a "forward" status to a "backward" one
                if from_str in FORWARD_STATUSES and to_str in BACKWARD_STATUSES:
                    reopens += 1

                detail.append({
                    'key': key,
                    'from': from_str,
                    'to': to_str,
                    'timestamp': entry.get('created', ''),
                    'is_reopen': from_str in FORWARD_STATUSES and to_str in BACKWARD_STATUSES,
                })

    detail.sort(key=lambda d: d['timestamp'], reverse=True)

    return {
        'transitions_by_pm': pm_transitions,
        'reopens_rejections': reopens,
        'breakdown': breakdown,
        'detail': detail,
    }


def _compute_scope_management(
    tickets: List[Dict],
    changelogs: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: List[str],
    sprint_start: Optional[str] = None,
) -> Dict[str, Any]:
    """
    E. Sprint Scope Management
    - Tickets added/removed mid-sprint
    - Assignment balance (CV of hours across devs)
    """
    sprint_start_dt = _parse_dt(sprint_start) if sprint_start else None
    added = []
    removed = []

    for key, entries in changelogs.items():
        for entry in entries:
            entry_dt = _parse_dt(entry.get('created'))
            for item in entry.get('items', []):
                if item.get('field') != 'Sprint':
                    continue
                to_str = item.get('toString') or ''
                from_str = item.get('fromString') or ''

                # If sprint_start_dt exists, only count changes after sprint started
                if sprint_start_dt and entry_dt and entry_dt <= sprint_start_dt:
                    continue

                author_name = entry.get('author', {}).get('displayName', '')
                author_id = entry.get('author', {}).get('accountId', '')

                if to_str and not from_str:
                    # Added to sprint (not moved between sprints)
                    pass
                if to_str:
                    added.append({
                        'key': key,
                        'by': author_name,
                        'by_id': author_id,
                        'timestamp': entry.get('created', ''),
                    })
                if from_str and not to_str:
                    removed.append({
                        'key': key,
                        'by': author_name,
                        'by_id': author_id,
                        'timestamp': entry.get('created', ''),
                    })

    # Assignment balance: coefficient of variation of hours per developer
    dev_hours: Dict[str, float] = {}
    for ticket in tickets:
        assignee = ticket.get('assignee_id') or ticket.get('assignee', 'Unassigned')
        hours = (ticket.get('original_estimate_seconds') or 0) / 3600
        dev_hours[assignee] = dev_hours.get(assignee, 0) + hours

    # Remove "Unassigned" from balance calculation
    dev_hours.pop('Unassigned', None)
    dev_hours.pop('', None)

    if len(dev_hours) >= 2:
        values = list(dev_hours.values())
        mean = sum(values) / len(values)
        if mean > 0:
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            cv = round((variance ** 0.5) / mean, 2)
        else:
            cv = 0.0
    else:
        cv = 0.0

    return {
        'tickets_added_mid_sprint': len(added),
        'tickets_removed_mid_sprint': len(removed),
        'assignment_balance_cv': cv,
        'detail': {
            'added': added,
            'removed': removed,
            'dev_hours': dev_hours,
        },
    }


def _compute_blocker_response(
    tickets: List[Dict],
    changelogs: Dict[str, List[Dict]],
    comments: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: List[str],
) -> Dict[str, Any]:
    """
    F. Blocker Response
    - Avg time from Blocked status → first PM comment
    - Blocked tickets with zero PM engagement after 24h
    """
    response_times = []
    no_engagement = []
    detail = []

    for ticket in tickets:
        key = ticket.get('key', '')
        entries = changelogs.get(key, [])

        # Find when ticket entered Blocked status
        blocked_at = None
        for entry in entries:
            for item in entry.get('items', []):
                if item.get('field') == 'status' and (item.get('toString') or '').strip() == 'Blocked':
                    blocked_at = _parse_dt(entry.get('created'))

        if not blocked_at:
            continue

        # Find first PM comment after blocked_at
        ticket_comments = comments.get(key, [])
        first_pm_after = None
        for c in sorted(ticket_comments, key=lambda x: x.get('created', '')):
            c_time = _parse_dt(c.get('created'))
            if not c_time or c_time <= blocked_at:
                continue
            author_id = c.get('author', {}).get('accountId')
            author_name = c.get('author', {}).get('displayName')
            if _pm_matches(author_id, author_name, pm_account_id, pm_names):
                first_pm_after = c_time
                break

        if first_pm_after:
            hours = _business_hours_between(blocked_at, first_pm_after)
            response_times.append(hours)
            detail.append({
                'key': key,
                'summary': ticket.get('summary', ''),
                'blocked_at': blocked_at.isoformat(),
                'pm_responded_at': first_pm_after.isoformat(),
                'response_hours': round(hours, 1),
            })
        else:
            # No PM engagement
            hours_since = _business_hours_between(blocked_at, datetime.utcnow())
            if hours_since >= 24:
                no_engagement.append(key)
            detail.append({
                'key': key,
                'summary': ticket.get('summary', ''),
                'blocked_at': blocked_at.isoformat(),
                'pm_responded_at': None,
                'response_hours': None,
                'hours_since_blocked': round(hours_since, 1),
            })

    avg_hours = round(sum(response_times) / len(response_times), 1) if response_times else None

    return {
        'avg_blocked_to_pm_comment_hours': avg_hours,
        'blocked_no_pm_engagement': len(no_engagement),
        'detail': detail,
    }


# ── Grading ───────────────────────────────────────────────────────────────────

def _grade_letter(value: float, thresholds: Dict, metric: str, higher_is_better: bool = False) -> str:
    """Assign A/B/C/D based on thresholds for a single metric within a group."""
    for grade in ('A', 'B', 'C'):
        threshold = thresholds[grade].get(metric)
        if threshold is None:
            continue
        if higher_is_better:
            if value >= threshold:
                return grade
        else:
            if value <= threshold:
                return grade
    return 'D'


GRADE_NUMERIC = {'A': 4, 'B': 3, 'C': 2, 'D': 1}


def _compute_grades(metrics: Dict, thresholds: Optional[Dict] = None) -> Dict[str, str]:
    """Compute letter grades for each metric group and overall."""
    t = thresholds or DEFAULT_THRESHOLDS

    grades = {}

    # A. Approval
    avg_pa = metrics.get('avg_pending_approval_hours') or 0
    backlog = metrics.get('pending_approval_backlog') or 0
    g1 = _grade_letter(avg_pa, t['approval'], 'avg_hours')
    g2 = _grade_letter(backlog, t['approval'], 'backlog')
    grades['approval'] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])

    # B. Engagement
    ratio = metrics.get('engagement_ratio') or 0
    grades['engagement'] = _grade_letter(ratio, t['engagement'], 'ratio', higher_is_better=True)

    # C. Responsiveness
    avg_resp = metrics.get('avg_pm_response_hours') or 0
    waiting = metrics.get('threads_waiting_on_pm') or 0
    g1 = _grade_letter(avg_resp, t['responsiveness'], 'avg_hours')
    g2 = _grade_letter(waiting, t['responsiveness'], 'waiting')
    grades['responsiveness'] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])

    # D. Grooming
    est_pct = metrics.get('estimation_coverage_pct') or 0
    grades['grooming'] = _grade_letter(est_pct, t['grooming'], 'estimation_pct', higher_is_better=True)

    # E. Transitions
    trans = metrics.get('transitions_by_pm') or 0
    reopens = metrics.get('reopens_rejections') or 0
    g1 = _grade_letter(trans, t['transitions'], 'min_transitions', higher_is_better=True)
    g2 = _grade_letter(reopens, t['transitions'], 'min_reopens', higher_is_better=True)
    grades['transitions'] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])

    # F. Blocker Response
    avg_block = metrics.get('avg_blocked_to_pm_comment_hours')
    no_eng = metrics.get('blocked_no_pm_engagement') or 0
    if avg_block is not None:
        g1 = _grade_letter(avg_block, t['blocker_response'], 'avg_hours')
        g2 = _grade_letter(no_eng, t['blocker_response'], 'no_engagement')
        grades['blocker_response'] = min(g1, g2, key=lambda g: GRADE_NUMERIC[g])
    else:
        # No blocked tickets — assume good
        grades['blocker_response'] = 'A'

    # Overall weighted average
    total_w = 0.0
    total_score = 0.0
    for group, weight in GRADE_WEIGHTS.items():
        g = grades.get(group, 'C')
        total_score += GRADE_NUMERIC[g] * weight
        total_w += weight

    avg_score = total_score / total_w if total_w > 0 else 2.0
    if avg_score >= 3.5:
        overall = 'A'
    elif avg_score >= 2.5:
        overall = 'B'
    elif avg_score >= 1.5:
        overall = 'C'
    else:
        overall = 'D'

    grades['overall'] = overall
    return grades


# ── Main Orchestrator ─────────────────────────────────────────────────────────

def compute_pm_audit(
    tickets: List[Dict],
    comments: Dict[str, List[Dict]],
    changelogs: Dict[str, List[Dict]],
    pm_account_id: str,
    pm_names: Optional[List[str]] = None,
    sprint_meta: Optional[Dict] = None,
    thresholds: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Compute full PM self-audit from raw data.

    Args:
        tickets: List of ticket dicts with keys: key, summary, status, assignee,
                 reporter_id, assignee_id, original_estimate_seconds
        comments: Dict mapping ticket key → list of comment dicts
        changelogs: Dict mapping ticket key → list of changelog entry dicts
        pm_account_id: Jira account ID of the PM
        pm_names: List of display name variants for the PM (for changelog matching)
        sprint_meta: Optional dict with sprint_id, sprint_name, start_date, end_date
        thresholds: Optional custom grading thresholds

    Returns:
        Dict with all metric groups, grades, and detail data.
    """
    pm_names = pm_names or []
    sprint_meta = sprint_meta or {}

    approval = _compute_approval_velocity(tickets, changelogs, pm_account_id, pm_names)
    engagement = _compute_comment_activity(tickets, comments, pm_account_id, pm_names)
    grooming = _compute_grooming(tickets, pm_account_id)
    transitions = _compute_transitions(changelogs, pm_account_id, pm_names)
    scope = _compute_scope_management(
        tickets, changelogs, pm_account_id, pm_names,
        sprint_start=sprint_meta.get('start_date'),
    )
    blocker = _compute_blocker_response(tickets, changelogs, comments, pm_account_id, pm_names)

    # Flatten metrics for grading
    metrics = {
        **{k: v for k, v in approval.items() if k != 'detail'},
        **{k: v for k, v in engagement.items() if k != 'detail'},
        **{k: v for k, v in grooming.items() if k != 'detail'},
        **{k: v for k, v in transitions.items() if k not in ('detail', 'breakdown')},
        **{k: v for k, v in scope.items() if k != 'detail'},
        **{k: v for k, v in blocker.items() if k != 'detail'},
    }

    grades = _compute_grades(metrics, thresholds)

    return {
        'pm_account_id': pm_account_id,
        'pm_display_name': pm_names[0] if pm_names else '',
        'sprint_id': sprint_meta.get('sprint_id', ''),
        'sprint_name': sprint_meta.get('sprint_name', ''),
        'computed_at': datetime.utcnow().isoformat() + 'Z',

        # Flat metrics
        **metrics,
        'transition_breakdown': transitions.get('breakdown', {}),

        # Grades
        'overall_grade': grades['overall'],
        'grades': grades,

        # Detail for drill-down
        'detail': {
            'approval': approval.get('detail', []),
            'engagement': engagement.get('detail', []),
            'grooming': grooming.get('detail', {}),
            'transitions': transitions.get('detail', []),
            'scope': scope.get('detail', {}),
            'blocker_response': blocker.get('detail', []),
        },
    }
