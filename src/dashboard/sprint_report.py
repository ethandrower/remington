"""
Sprint Report Compute Layer

Pure Python math functions that mirror the Vue.js computed properties in
dashboard.html. Takes raw data from Jira API responses and produces a
fully computed, agent-ready sprint report.

No Flask, no Jira calls — pure computation only.
"""

from datetime import date, datetime, timedelta
from typing import Optional


# ── Helpers ──────────────────────────────────────────────────────────────────

def biz_days(start_str: str, end_str: str) -> int:
    """Count Mon-Fri business days between two YYYY-MM-DD strings (exclusive of end)."""
    if not start_str or not end_str:
        return 0
    try:
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
    except ValueError:
        return 0
    if end <= start:
        return 0
    count = 0
    cur = start
    while cur < end:
        if cur.weekday() < 5:
            count += 1
        cur += timedelta(days=1)
    return count


def _score_ticket(ticket: dict, weights: dict) -> float:
    """Per-ticket health score (0.0–1.0). Mirrors _spScore() in dashboard.html."""
    sw = weights.get(ticket.get('status', ''), 0.05)
    est = ticket.get('estimate_hours') or 0
    logged = ticket.get('logged_hours') or 0
    time_ratio = min(logged / est, 1.0) if est > 0 else 0.0
    if sw >= 0.90:
        time_ratio = 1.0
    return (sw * 0.6) + (time_ratio * 0.4)


def _cap_label(ratio: float) -> str:
    """Capacity status label. Mirrors spCapLabel()."""
    if ratio > 1.4:
        return 'Overloaded'
    if ratio > 1.0:
        return 'Tight'
    if ratio > 0.6:
        return 'Balanced'
    return 'Light'


# ── Sprint-wide computations ──────────────────────────────────────────────────

def compute_health_score(developers: list, weights: dict) -> int:
    """Sprint-wide health score (0–100). Mirrors spHealthScore."""
    sum_w = 0.0
    sum_est = 0.0
    for dev in developers:
        for t in dev.get('tickets', []):
            score = _score_ticket(t, weights)
            est = t.get('estimate_hours') or 1
            sum_w += score * est
            sum_est += est
    return round((sum_w / sum_est) * 100) if sum_est > 0 else 0


def compute_grade(health_score: int) -> dict:
    """Sprint grade label + color. Mirrors spGrade."""
    if health_score >= 80:
        return {'label': 'Healthy', 'color': 'green'}
    if health_score >= 65:
        return {'label': 'On Track', 'color': 'blue'}
    if health_score >= 45:
        return {'label': 'At Risk', 'color': 'yellow'}
    return {'label': 'Behind', 'color': 'red'}


def compute_bar_segments(developers: list, weights: dict) -> list:
    """Status distribution buckets. Mirrors spBarSegments."""
    buckets = {
        'done':    {'label': 'Done',        'ticket_keys': [], 'hours': 0.0},
        'qa':      {'label': 'QA / Review', 'ticket_keys': [], 'hours': 0.0},
        'active':  {'label': 'In Progress', 'ticket_keys': [], 'hours': 0.0},
        'todo':    {'label': 'Not Started', 'ticket_keys': [], 'hours': 0.0},
        'blocked': {'label': 'Blocked',     'ticket_keys': [], 'hours': 0.0},
    }
    total_est = 0.0
    for dev in developers:
        for t in dev.get('tickets', []):
            sw = weights.get(t.get('status', ''), 0.05)
            est = t.get('estimate_hours') or 0
            total_est += est
            if sw >= 0.90:
                key = 'done'
            elif sw >= 0.50:
                key = 'qa'
            elif sw >= 0.15:
                key = 'active'
            elif sw > 0.03:
                key = 'todo'
            else:
                key = 'blocked'
            buckets[key]['ticket_keys'].append(t.get('key', ''))
            buckets[key]['hours'] += est

    result = []
    for key, b in buckets.items():
        pct = round(b['hours'] / total_est * 100, 1) if total_est > 0 else 0.0
        result.append({
            'key':     key,
            'label':   b['label'],
            'tickets': len(b['ticket_keys']),
            'hours':   round(b['hours'], 1),
            'pct':     pct,
        })
    return result


def compute_why_behind(developers: list, weights: dict, biz_days_left: int) -> list:
    """Narrative reasons list. Mirrors spWhyBehind()."""
    today = date.today().isoformat()
    all_tickets = [t for d in developers for t in d.get('tickets', [])]

    blocked = [t for t in all_tickets
               if (weights.get(t.get('status', ''), 0.05) <= 0.02)]
    overdue = [t for t in all_tickets
               if t.get('due_date') and t['due_date'] < today
               and (weights.get(t.get('status', ''), 0.05) < 0.90)]
    unestimated = [t for t in all_tickets if not t.get('estimate_hours')]
    changes_req = [t for t in all_tickets
                   if 0.50 <= (weights.get(t.get('status', ''), 0.05)) < 0.65]

    reasons = []
    if blocked:
        n = len(blocked)
        reasons.append(f"{n} blocked ticket{'s' if n > 1 else ''}")
    if overdue:
        n = len(overdue)
        reasons.append(f"{n} overdue ticket{'s' if n > 1 else ''}")

    for dev in developers:
        m = _compute_dev_metrics_inner(dev, weights, biz_days_left)
        if m['capacity_ratio'] > 1.2:
            pct = round(m['capacity_ratio'] * 100)
            reasons.append(f"{dev.get('name', 'Unknown')} overloaded at {pct}% capacity")

    if changes_req:
        n = len(changes_req)
        reasons.append(f"{n} ticket{'s' if n > 1 else ''} need QA changes / rework")
    if unestimated:
        n = len(unestimated)
        reasons.append(f"{n} unestimated ticket{'s' if n > 1 else ''}")

    return reasons


def compute_action_items(developers: list, weights: dict) -> list:
    """Sorted critical/warning action items. Mirrors spActionItems()."""
    today = date.today().isoformat()
    items = []
    for dev in developers:
        for t in dev.get('tickets', []):
            sw = weights.get(t.get('status', ''), 0.05)
            due = t.get('due_date')
            if sw <= 0.02:
                items.append({
                    'severity': 'critical',
                    'type': 'blocked',
                    'ticket': t.get('key'),
                    'summary': t.get('summary', ''),
                    'dev': dev.get('name', ''),
                    'due_date': due,
                })
            elif due and due < today and sw < 0.90:
                items.append({
                    'severity': 'critical',
                    'type': 'overdue',
                    'ticket': t.get('key'),
                    'summary': t.get('summary', ''),
                    'dev': dev.get('name', ''),
                    'due_date': due,
                })
            elif 0.50 <= sw < 0.65:
                items.append({
                    'severity': 'warning',
                    'type': 'changes_requested',
                    'ticket': t.get('key'),
                    'summary': t.get('summary', ''),
                    'dev': dev.get('name', ''),
                    'due_date': due,
                })
    items.sort(key=lambda x: (0 if x['severity'] == 'critical' else 1,
                               x.get('due_date') or '9999'))
    return items


# ── Per-developer computations ────────────────────────────────────────────────

def _compute_dev_metrics_inner(dev: dict, weights: dict, biz_days_left: int) -> dict:
    """Per-developer metrics. Mirrors spDevMetrics()."""
    today = date.today().isoformat()
    avail_hours = biz_days_left * 6.0
    hours_remaining = 0.0
    overdue, blocked, changes_req, unestimated, not_started = [], [], [], [], []
    completed = 0

    for t in dev.get('tickets', []):
        sw = weights.get(t.get('status', ''), 0.05)
        if sw >= 0.90:
            completed += 1
            continue
        est = t.get('estimate_hours') or 0
        logged = t.get('logged_hours') or 0
        rem = max(0.0, est - logged)
        hours_remaining += rem
        if t.get('due_date') and t['due_date'] < today:
            overdue.append(t.get('key'))
        if sw <= 0.02:
            blocked.append(t.get('key'))
        elif 0.50 <= sw < 0.65:
            changes_req.append(t.get('key'))
        if not est:
            unestimated.append(t.get('key'))
        if sw <= 0.10:
            not_started.append(t.get('key'))

    capacity_ratio = hours_remaining / avail_hours if avail_hours > 0 else 0.0
    return {
        'health_score':    _dev_health_score(dev, weights),
        'capacity_ratio':  round(capacity_ratio, 2),
        'capacity_label':  _cap_label(capacity_ratio),
        'hours_remaining': round(hours_remaining, 1),
        'avail_hours':     round(avail_hours, 1),
        'completed':       completed,
        'total_tickets':   len(dev.get('tickets', [])),
        'overdue':         overdue,
        'blocked':         blocked,
        'changes_req':     changes_req,
        'unestimated':     unestimated,
        'not_started':     not_started,
    }


def _dev_health_score(dev: dict, weights: dict) -> int:
    """Mirrors spDevHealthScore()."""
    sum_w = 0.0
    sum_est = 0.0
    for t in dev.get('tickets', []):
        score = _score_ticket(t, weights)
        est = t.get('estimate_hours') or 1
        sum_w += score * est
        sum_est += est
    return round((sum_w / sum_est) * 100) if sum_est > 0 else 0


def _health_reasons(m: dict) -> list:
    """Mirrors spHealthReasons(). Takes output of _compute_dev_metrics_inner."""
    reasons = []
    if m['overdue']:
        n = len(m['overdue'])
        reasons.append({'severity': 'critical',
                        'text': f"{n} overdue ticket{'s' if n > 1 else ''}"})
    if m['blocked']:
        n = len(m['blocked'])
        reasons.append({'severity': 'critical',
                        'text': f"{n} blocked ticket{'s' if n > 1 else ''}"})
    if m['capacity_ratio'] > 1.4:
        reasons.append({'severity': 'warning',
                        'text': f"Overloaded — {m['hours_remaining']}h remaining vs {m['avail_hours']}h available"})
    elif m['capacity_ratio'] > 1.0:
        days_est = round(m['avail_hours'] / 6) if m['avail_hours'] else 0
        reasons.append({'severity': 'warning',
                        'text': f"Tight capacity — {m['hours_remaining']}h remaining, {days_est} days left"})
    if m['changes_req']:
        n = len(m['changes_req'])
        reasons.append({'severity': 'warning',
                        'text': f"{n} ticket{'s' if n > 1 else ''} need changes / rework"})
    if m['unestimated']:
        n = len(m['unestimated'])
        reasons.append({'severity': 'info',
                        'text': f"{n} unestimated ticket{'s' if n > 1 else ''} — capacity may be understated"})
    if m['completed'] > 0 and not reasons:
        n = m['completed']
        reasons.append({'severity': 'success',
                        'text': f"{n} ticket{'s' if n > 1 else ''} completed — on track"})
    if not reasons:
        reasons.append({'severity': 'info', 'text': 'No immediate issues detected'})
    return reasons


def compute_dev_projections(dev: dict, weights: dict, biz_days_left: int) -> list:
    """Per-ticket risk projections. Mirrors spProjections()."""
    today = date.today().isoformat()
    open_tickets = [t for t in dev.get('tickets', [])
                    if (weights.get(t.get('status', ''), 0.05) < 0.90)]
    total_rem = sum(
        max(0, (t.get('estimate_hours') or 0) - (t.get('logged_hours') or 0))
        for t in open_tickets
    )
    hours_per_day = min(total_rem / biz_days_left, 6.0) if biz_days_left > 0 else 6.0

    result = []
    for t in open_tickets:
        est = t.get('estimate_hours') or 0
        logged = t.get('logged_hours') or 0
        effective_rem = max(0.0, est - logged)
        days_needed = effective_rem / hours_per_day if hours_per_day > 0 else 99
        due = t.get('due_date')
        hours_to_deadline = biz_days(today, due) * 6 if (due and due >= today) else None

        if due and due < today:
            risk = 'critical'
            projection = 'OVERDUE'
            detail = f"Due {due} — already past deadline"
        elif hours_to_deadline is not None and effective_rem > hours_to_deadline:
            risk = 'critical'
            projection = 'AT RISK'
            detail = f"Needs {round(effective_rem, 1)}h but only {hours_to_deadline}h until deadline"
        elif days_needed > biz_days_left * 0.8:
            risk = 'warning'
            projection = 'TIGHT'
            detail = f"~{round(days_needed)} days of work, {biz_days_left} days left"
        else:
            risk = 'none'
            projection = 'On Track'
            detail = f"~{round(days_needed)} days needed" if est else 'No estimate'

        result.append({
            'key':             t.get('key'),
            'summary':         t.get('summary', ''),
            'status':          t.get('status', ''),
            'risk':            risk,
            'projection':      projection,
            'detail':          detail,
            'estimate_hours':  est,
            'logged_hours':    logged,
            'remaining_hours': round(effective_rem, 1),
            'due_date':        due,
        })

    result.sort(key=lambda x: {'critical': 0, 'warning': 1, 'none': 2}.get(x['risk'], 3))
    return result


def compute_performance_devs(
    developers: list,
    weights: dict,
    team_members: list,
    biz_days_left: int,
    total_biz_days: int,
    sprint_pct_elapsed: float,
    sprint_weeks: float,
) -> list:
    """
    Per-developer velocity + performance classification.
    Mirrors spPerformanceDevs computed property — the richest in the dashboard.

    team_members: list of dicts from dashboard DB (is_active, role, jira_account_id, etc.)
    """
    dev_map = {d['account_id']: d for d in developers}
    ROLES = {'dev', 'wa', 'tech_lead'}
    result = []

    for m in team_members:
        if not m.get('is_active'):
            continue
        role = (m.get('role') or '').lower()
        if role not in ROLES:
            continue
        jira_id = m.get('jira_account_id')
        if not jira_id:
            continue

        sp_dev = dev_map.get(jira_id, {'tickets': [], 'account_id': jira_id,
                                        'name': m.get('display_name', '')})
        tickets = sp_dev.get('tickets', [])

        def sw(t):
            return weights.get(t.get('status', ''), 0.05) or 0

        total_tix  = len(tickets)
        done_tix   = sum(1 for t in tickets if sw(t) >= 0.9)
        near_tix   = sum(1 for t in tickets if 0.5 <= sw(t) < 0.9)
        active_tix = sum(1 for t in tickets if 0.15 <= sw(t) < 0.5)

        total_h  = sum(t.get('estimate_hours') or 0 for t in tickets)
        done_h   = sum(t.get('estimate_hours') or 0 for t in tickets if sw(t) >= 0.9)
        near_h   = sum(t.get('estimate_hours') or 0 for t in tickets if 0.5 <= sw(t) < 0.9)
        active_h = sum(t.get('estimate_hours') or 0 for t in tickets if 0.15 <= sw(t) < 0.5)

        has_estimates = total_h > total_tix  # avg > 1h/ticket

        if has_estimates:
            actual_done_pct = done_h / total_h if total_h > 0 else 0.0
        else:
            actual_done_pct = done_tix / total_tix if total_tix > 0 else 0.0

        ideal_done_pct = min(sprint_pct_elapsed, 1.0)
        gap = actual_done_pct - ideal_done_pct

        wk_cap = float(m.get('weekly_capacity_hours') or 40)
        capacity_h = wk_cap * sprint_weeks
        remaining_cap_h = biz_days_left * (wk_cap / 5.0)
        remaining_work_h = total_h - done_h
        remaining_tix = total_tix - done_tix

        overloaded = total_h > capacity_h * 1.05

        ideal_daily_tix = total_tix / total_biz_days if total_biz_days > 0 else 0
        at_risk = (
            not overloaded and gap < -0.10 and (
                (has_estimates
                 and remaining_cap_h > 0
                 and remaining_work_h > remaining_cap_h * 1.05)
                or (not has_estimates
                    and biz_days_left > 0
                    and ideal_daily_tix > 0
                    and (remaining_tix / biz_days_left) > ideal_daily_tix * 1.5)
            )
        )

        if total_tix == 0:
            v_status, v_label = 'no_tickets', 'No tickets'
        elif overloaded:
            v_status, v_label = 'overloaded', 'Overloaded'
        elif at_risk:
            v_status, v_label = 'at_risk', 'Behind — At Risk'
        elif gap < -0.15 and ideal_done_pct > 0.05:
            v_status, v_label = 'behind', 'Behind'
        elif gap > 0.1:
            v_status, v_label = 'ahead', 'Ahead'
        else:
            v_status, v_label = 'on_track', 'On Track'

        dev_m = _compute_dev_metrics_inner(sp_dev, weights, biz_days_left)
        projections = compute_dev_projections(sp_dev, weights, biz_days_left)

        result.append({
            'name':                     m['display_name'],
            'role':                     role,
            'jira_account_id':          jira_id,
            'velocity_status':          v_status,
            'velocity_label':           v_label,
            'actual_done_pct':          round(actual_done_pct * 100),
            'ideal_done_pct':           round(ideal_done_pct * 100),
            'gap':                      round(gap * 100),
            'capacity_hours':           round(capacity_h, 1),
            'remaining_capacity_hours': round(remaining_cap_h, 1),
            'remaining_work_hours':     round(remaining_work_h, 1),
            'capacity_label':           dev_m['capacity_label'],
            'health_score':             dev_m['health_score'],
            'ticket_summary': {
                'total':       total_tix,
                'done':        done_tix,
                'near_done':   near_tix,
                'active':      active_tix,
                'blocked':     len(dev_m['blocked']),
                'overdue':     len(dev_m['overdue']),
                'unestimated': len(dev_m['unestimated']),
            },
            'health_reasons':  _health_reasons(dev_m),
            'tickets_at_risk': [p for p in projections if p['risk'] in ('critical', 'warning')],
            'all_projections': projections,
        })

    ORDER = {'overloaded': 0, 'at_risk': 1, 'behind': 2, 'on_track': 3, 'ahead': 4, 'no_tickets': 5}
    result.sort(key=lambda d: (ORDER.get(d['velocity_status'], 6), d.get('gap', 0)))
    return result


# ── Planning summary ──────────────────────────────────────────────────────────

def compute_planning_summary(planning_data: dict) -> Optional[dict]:
    """Next-sprint capacity summary. Mirrors planningAuditBlocks() math."""
    if not planning_data:
        return None

    devs = planning_data.get('developers', [])
    sprint = planning_data.get('sprint', {})

    total_capacity = round(sum(d.get('capacity_hours', 0) for d in devs), 1)
    total_planned  = round(sum(d.get('planned_hours', 0) for d in devs), 1)
    total_rollover = round(sum(d.get('rollover_hours', 0) for d in devs), 1)
    total_load     = round(total_planned + total_rollover, 1)
    unassigned_h   = round(sum(t.get('estimate_hours') or 0
                               for t in planning_data.get('unassigned_tickets', [])), 1)

    load_pct = round(total_load / total_capacity * 100) if total_capacity > 0 else 0

    if load_pct > 100:
        status = 'Overloaded'
    elif load_pct > 85:
        status = 'Tight'
    else:
        status = 'Healthy'

    dev_summaries = []
    for d in devs:
        cap  = d.get('capacity_hours') or 0
        load = d.get('total_load_hours') or 0
        buf  = round(cap - load, 1)
        p    = load / cap if cap > 0 else 0
        dev_status = 'Overloaded' if p > 1.05 else ('Tight' if p > 0.85 else 'OK')
        dev_summaries.append({
            'name':           d.get('display_name', ''),
            'role':           d.get('role', ''),
            'capacity_hours': round(cap, 1),
            'planned_hours':  round(d.get('planned_hours') or 0, 1),
            'rollover_hours': round(d.get('rollover_hours') or 0, 1),
            'total_load':     round(load, 1),
            'buffer_hours':   buf,
            'status':         dev_status,
        })

    rollover_ctx = planning_data.get('rollover_context') or {}

    # Group per-dev summaries by team track
    dev_track    = [d for d in dev_summaries if d['role'] in ('dev', 'tech_lead')]
    design_track = [d for d in dev_summaries if d['role'] == 'wa']

    def _track_totals(members):
        cap  = sum(d['capacity_hours'] for d in members)
        load = sum(d['total_load'] for d in members)
        return {
            'capacity_hours': round(cap, 1),
            'load_hours':     round(load, 1),
            'load_pct':       round(load / cap * 100) if cap else 0,
            'status':         'Overloaded' if load > cap * 1.05
                              else ('Tight' if load > cap * 0.85 else 'Healthy'),
        }

    teams_planning = []
    if dev_track:
        teams_planning.append({
            'key': 'dev_team', 'label': 'Dev Team',
            **_track_totals(dev_track),
            'developers': dev_track,
        })
    if design_track:
        teams_planning.append({
            'key': 'design_team', 'label': 'Design Team',
            **_track_totals(design_track),
            'developers': design_track,
        })

    return {
        'sprint_name':          sprint.get('name', ''),
        'sprint_start':         sprint.get('start_date'),
        'sprint_end':           sprint.get('end_date'),
        'total_capacity_hours': total_capacity,
        'total_planned_hours':  total_planned,
        'rollover_hours':       total_rollover,
        'total_load_hours':     total_load,
        'available_hours':      round(total_capacity - total_load, 1),
        'load_pct':             load_pct,
        'status':               status,
        'unassigned_hours':     unassigned_h,
        'unassigned_tickets':   len(planning_data.get('unassigned_tickets', [])),
        'rollover_context':     rollover_ctx,
        'developers':           dev_summaries,
        'teams':                teams_planning,
    }


# ── Team grouping ────────────────────────────────────────────────────────────

def _compute_teams(performance_devs: list, raw_devs: list, weights: dict) -> list:
    """
    Group developers into parallel-track team summaries.

    Dev Track:    role == 'dev' or 'tech_lead'
    Design Track: role == 'wa'

    Each team entry includes aggregate health score, status distribution,
    and a summary of worst velocity statuses — so agents can report on
    each track independently without iterating the full developer list.
    """
    TRACK_MAP = {
        'dev':       'dev_team',
        'tech_lead': 'dev_team',
        'wa':        'design_team',
    }

    tracks: dict = {}

    for dev in performance_devs:
        track_key = TRACK_MAP.get(dev.get('role', ''), 'dev_team')
        if track_key not in tracks:
            tracks[track_key] = {
                'key':        track_key,
                'label':      'Dev Team' if track_key == 'dev_team' else 'Design Team',
                'members':    [],
                'all_devs':   [],
            }
        tracks[track_key]['all_devs'].append(dev)
        tracks[track_key]['members'].append({
            'name':            dev['name'],
            'role':            dev['role'],
            'velocity_status': dev['velocity_status'],
            'velocity_label':  dev['velocity_label'],
            'health_score':    dev['health_score'],
            'gap':             dev['gap'],
            'ticket_summary':  dev['ticket_summary'],
        })

    # If we have no performance_devs (no team_members provided), fall back to
    # grouping raw Jira developers by jira-side data only (no velocity status)
    if not performance_devs and raw_devs:
        fallback: dict = {'dev_team': {'key': 'dev_team', 'label': 'Dev Team',
                                        'members': [], 'all_devs': []}}
        for dev in raw_devs:
            if dev.get('account_id') == 'unassigned':
                continue
            fallback['dev_team']['members'].append({
                'name':            dev.get('name', ''),
                'role':            'dev',
                'velocity_status': 'unknown',
                'velocity_label':  'Unknown',
                'health_score':    None,
                'gap':             None,
                'ticket_summary':  {
                    'total': len(dev.get('tickets', [])),
                },
            })
        tracks = fallback

    result = []
    ORDER = {'overloaded': 0, 'at_risk': 1, 'behind': 2, 'on_track': 3,
             'ahead': 4, 'no_tickets': 5, 'unknown': 6}

    for track in tracks.values():
        all_devs = track.pop('all_devs', [])

        # Aggregate ticket counts across the track
        total_tix  = sum(d['ticket_summary'].get('total', 0) for d in all_devs)
        done_tix   = sum(d['ticket_summary'].get('done', 0) for d in all_devs)
        blocked_tix = sum(d['ticket_summary'].get('blocked', 0) for d in all_devs)
        overdue_tix = sum(d['ticket_summary'].get('overdue', 0) for d in all_devs)

        # Aggregate health score (average, weighted by ticket count)
        scored = [(d['health_score'], d['ticket_summary'].get('total', 1))
                  for d in all_devs if d.get('health_score') is not None]
        if scored:
            total_w = sum(w for _, w in scored)
            agg_health = round(sum(s * w for s, w in scored) / total_w) if total_w else 0
        else:
            agg_health = None

        # Worst velocity status in the track
        statuses = [d['velocity_status'] for d in all_devs if d.get('velocity_status')]
        worst_status = min(statuses, key=lambda s: ORDER.get(s, 99)) if statuses else None

        track['ticket_summary'] = {
            'total':   total_tix,
            'done':    done_tix,
            'blocked': blocked_tix,
            'overdue': overdue_tix,
        }
        track['health_score']    = agg_health
        track['worst_velocity']  = worst_status
        track['member_count']    = len(track['members'])
        result.append(track)

    # Dev Team first, then Design Team
    result.sort(key=lambda t: 0 if t['key'] == 'dev_team' else 1)
    return result


# ── Main orchestrator ─────────────────────────────────────────────────────────

def build_report(
    pulse_data: dict,
    burndown_data: dict,
    planning_data: Optional[dict] = None,
    team_members: Optional[list] = None,
) -> dict:
    """
    Build a fully computed agent-ready sprint report from raw API data.

    Args:
        pulse_data:    Response dict from /api/sprint-pulse
        burndown_data: Response dict from /api/sprint-burndown
        planning_data: Optional response dict from /api/sprint-planning
        team_members:  Optional list from DB (enables velocity classification per dev)

    Returns:
        Comprehensive dict ready for JSON serialisation.
    """
    sprint   = pulse_data.get('sprint', {})
    devs     = pulse_data.get('developers', [])
    weights  = pulse_data.get('status_weights', {})
    jira_url = pulse_data.get('jira_url', '')

    today      = date.today().isoformat()
    start_date = sprint.get('start_date') or today
    end_date   = sprint.get('end_date') or today

    total_biz   = biz_days(start_date, end_date)
    elapsed     = biz_days(start_date, today)
    days_left   = biz_days(today, end_date)
    pct_elapsed = min(elapsed / total_biz, 1.0) if total_biz > 0 else 0.0

    try:
        sd = date.fromisoformat(start_date)
        ed = date.fromisoformat(end_date)
        sprint_weeks = max(1.0, round((ed - sd).days / 7, 1))
    except Exception:
        sprint_weeks = 2.0

    health_score = compute_health_score(devs, weights)
    grade        = compute_grade(health_score)
    segments     = compute_bar_segments(devs, weights)
    why_behind   = compute_why_behind(devs, weights, days_left)
    action_items = compute_action_items(devs, weights)

    performance_devs = []
    if team_members:
        performance_devs = compute_performance_devs(
            devs, weights, team_members,
            days_left, total_biz, pct_elapsed, sprint_weeks,
        )

    # Split developers into parallel tracks (Dev Team / Design Team)
    teams = _compute_teams(performance_devs, devs, weights)

    # Burndown summary
    bd = burndown_data or {}
    snapshots = bd.get('daily_snapshots') or []
    latest_snap = snapshots[-1] if snapshots else {}
    burndown_summary = {
        'total_hours':          bd.get('total_hours', 0),
        'initial_hours':        bd.get('initial_hours', 0),
        'complete_hours':       bd.get('complete_hours', 0),
        'complete_pct':         bd.get('complete_pct', 0),
        'remaining_hours':      latest_snap.get('remaining', 0),
        'ideal_hours_now':      latest_snap.get('ideal', 0),
        'behind_hours':         bd.get('behind_hours', 0),
        'blocked_hours':        bd.get('blocked_hours', 0),
        'scope_added_hours':    bd.get('added_hours', 0),
        'scope_added_tickets':  bd.get('added_tickets', 0),
        'scope_additions':      bd.get('scope_additions', []),
    }

    return {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'jira_url':     jira_url,
        'sprint': {
            'name':                sprint.get('name', ''),
            'start_date':          start_date,
            'end_date':            end_date,
            'days_elapsed':        elapsed,
            'total_business_days': total_biz,
            'days_remaining':      days_left,
            'pct_elapsed':         round(pct_elapsed * 100),
        },
        'health': {
            'score':               health_score,
            'grade':               grade['label'],
            'color':               grade['color'],
            'status_distribution': {s['key']: {k: v for k, v in s.items() if k != 'key'}
                                    for s in segments},
            'why_behind':          why_behind,
        },
        'burndown':     burndown_summary,
        'action_items': action_items,
        'developers':   performance_devs,
        'teams':        teams,
        'next_sprint':  compute_planning_summary(planning_data),
    }
