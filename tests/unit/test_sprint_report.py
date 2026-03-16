"""
Unit tests for src/dashboard/sprint_report.py

All tests are pure-Python — no Flask, no Jira, no DB.
"""

import pytest
from datetime import date, timedelta
from src.dashboard.sprint_report import (
    biz_days,
    _score_ticket,
    _cap_label,
    compute_health_score,
    compute_grade,
    compute_bar_segments,
    compute_why_behind,
    compute_action_items,
    compute_dev_projections,
    compute_performance_devs,
    compute_planning_summary,
    build_report,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

WEIGHTS = {
    'Done':              1.0,
    'Pending Approval':  0.92,
    'In QA':             0.85,
    'In Progress':       0.35,
    'Blocked':           0.02,
    'Ready for Dev':     0.05,
}


def _ticket(key='ECD-1', status='In Progress', est=8.0, logged=0.0, due=None):
    return {'key': key, 'summary': f'Summary {key}', 'status': status,
            'estimate_hours': est, 'logged_hours': logged, 'due_date': due}


def _dev(name='Alice', account_id='alice', tickets=None):
    return {'name': name, 'account_id': account_id, 'tickets': tickets or []}


def _today():
    return date.today().isoformat()


def _days_ahead(n):
    return (date.today() + timedelta(days=n)).isoformat()


def _days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def _sprint(start_offset=-5, end_offset=5):
    """Active sprint spanning from N days ago to M days ahead."""
    return {
        'name': 'Sprint Test',
        'start_date': (date.today() + timedelta(days=start_offset)).isoformat(),
        'end_date':   (date.today() + timedelta(days=end_offset)).isoformat(),
    }


def _pulse_data(devs=None, sprint=None):
    return {
        'sprint':         sprint or _sprint(),
        'developers':     devs or [],
        'status_weights': WEIGHTS,
        'jira_url':       'https://example.atlassian.net',
    }


def _burndown_data(behind=0.0, complete_pct=50.0, remaining=20.0):
    return {
        'total_hours': 40.0,
        'initial_hours': 40.0,
        'complete_hours': 40.0 * complete_pct / 100,
        'complete_pct': complete_pct,
        'behind_hours': behind,
        'blocked_hours': 0.0,
        'added_hours': 0.0,
        'added_tickets': 0,
        'scope_additions': [],
        'daily_snapshots': [
            {'date': _today(), 'remaining': remaining, 'ideal': remaining - behind}
        ],
    }


# ── biz_days ──────────────────────────────────────────────────────────────────

class TestBizDays:
    def test_zero_when_same_date(self):
        assert biz_days('2026-03-16', '2026-03-16') == 0

    def test_zero_when_end_before_start(self):
        assert biz_days('2026-03-16', '2026-03-10') == 0

    def test_one_weekday(self):
        # Monday to Tuesday = 1 business day
        assert biz_days('2026-03-16', '2026-03-17') == 1

    def test_excludes_weekend(self):
        # Monday to following Monday = 5 business days (Tue–Fri + Mon)
        assert biz_days('2026-03-16', '2026-03-23') == 5

    def test_full_two_week_sprint(self):
        # 10 business days over a 2-week sprint (Mon–Fri each week)
        assert biz_days('2026-03-16', '2026-03-28') == 10

    def test_empty_strings_return_zero(self):
        assert biz_days('', '2026-03-16') == 0
        assert biz_days('2026-03-16', '') == 0

    def test_invalid_date_returns_zero(self):
        assert biz_days('not-a-date', '2026-03-16') == 0


# ── _score_ticket ─────────────────────────────────────────────────────────────

class TestScoreTicket:
    def test_done_ticket_scores_1(self):
        t = _ticket(status='Done', est=8, logged=4)
        assert _score_ticket(t, WEIGHTS) == pytest.approx(1.0)

    def test_blocked_ticket_scores_low(self):
        t = _ticket(status='Blocked', est=8, logged=0)
        score = _score_ticket(t, WEIGHTS)
        assert score < 0.1

    def test_fully_logged_in_progress(self):
        t = _ticket(status='In Progress', est=8, logged=8)
        score = _score_ticket(t, WEIGHTS)
        # sw=0.35 * 0.6 + 1.0 * 0.4 = 0.21 + 0.40 = 0.61
        assert score == pytest.approx(0.61)

    def test_unestimated_ticket_no_time_ratio(self):
        t = _ticket(status='In Progress', est=0, logged=0)
        score = _score_ticket(t, WEIGHTS)
        # sw=0.35 * 0.6 + 0 * 0.4 = 0.21
        assert score == pytest.approx(0.21)

    def test_unknown_status_uses_fallback(self):
        t = _ticket(status='Weird Custom Status', est=4, logged=0)
        score = _score_ticket(t, WEIGHTS)
        # fallback sw=0.05
        assert 0.0 < score < 0.1

    def test_logged_capped_at_estimate(self):
        t = _ticket(status='In Progress', est=4, logged=100)
        score = _score_ticket(t, WEIGHTS)
        # time_ratio capped at 1.0: 0.35*0.6 + 1.0*0.4 = 0.61
        assert score == pytest.approx(0.61)


# ── _cap_label ────────────────────────────────────────────────────────────────

class TestCapLabel:
    def test_overloaded(self):
        assert _cap_label(1.5) == 'Overloaded'

    def test_tight(self):
        assert _cap_label(1.1) == 'Tight'

    def test_balanced(self):
        assert _cap_label(0.8) == 'Balanced'

    def test_light(self):
        assert _cap_label(0.4) == 'Light'

    def test_boundary_overloaded(self):
        assert _cap_label(1.41) == 'Overloaded'

    def test_boundary_tight(self):
        assert _cap_label(1.01) == 'Tight'


# ── compute_health_score ──────────────────────────────────────────────────────

class TestComputeHealthScore:
    def test_all_done_is_100(self):
        devs = [_dev(tickets=[_ticket(status='Done', est=8, logged=8)])]
        assert compute_health_score(devs, WEIGHTS) == 100

    def test_all_blocked_is_low(self):
        devs = [_dev(tickets=[_ticket(status='Blocked', est=8, logged=0)])]
        score = compute_health_score(devs, WEIGHTS)
        assert score < 5

    def test_empty_sprint_returns_zero(self):
        assert compute_health_score([], WEIGHTS) == 0

    def test_mixed_tickets_weighted_by_estimate(self):
        # Large done ticket should dominate
        devs = [_dev(tickets=[
            _ticket('ECD-1', 'Done', est=40, logged=40),
            _ticket('ECD-2', 'Blocked', est=1, logged=0),
        ])]
        score = compute_health_score(devs, WEIGHTS)
        assert score > 80  # dominated by 40h done ticket

    def test_multiple_devs_combined(self):
        devs = [
            _dev('Alice', tickets=[_ticket('ECD-1', 'Done', est=8, logged=8)]),
            _dev('Bob',   tickets=[_ticket('ECD-2', 'Done', est=8, logged=8)]),
        ]
        assert compute_health_score(devs, WEIGHTS) == 100


# ── compute_grade ─────────────────────────────────────────────────────────────

class TestComputeGrade:
    def test_healthy(self):
        g = compute_grade(85)
        assert g['label'] == 'Healthy'
        assert g['color'] == 'green'

    def test_on_track(self):
        assert compute_grade(70)['label'] == 'On Track'

    def test_at_risk(self):
        assert compute_grade(50)['label'] == 'At Risk'

    def test_behind(self):
        assert compute_grade(30)['label'] == 'Behind'

    def test_boundaries(self):
        assert compute_grade(80)['label'] == 'Healthy'
        assert compute_grade(79)['label'] == 'On Track'
        assert compute_grade(65)['label'] == 'On Track'
        assert compute_grade(64)['label'] == 'At Risk'
        assert compute_grade(45)['label'] == 'At Risk'
        assert compute_grade(44)['label'] == 'Behind'


# ── compute_bar_segments ──────────────────────────────────────────────────────

class TestComputeBarSegments:
    def test_returns_five_segments(self):
        segs = compute_bar_segments([], WEIGHTS)
        keys = {s['key'] for s in segs}
        assert keys == {'done', 'qa', 'active', 'todo', 'blocked'}

    def test_done_ticket_lands_in_done_bucket(self):
        devs = [_dev(tickets=[_ticket(status='Done', est=8)])]
        segs = {s['key']: s for s in compute_bar_segments(devs, WEIGHTS)}
        assert segs['done']['tickets'] == 1
        assert segs['done']['hours'] == 8.0

    def test_blocked_ticket_lands_in_blocked_bucket(self):
        devs = [_dev(tickets=[_ticket(status='Blocked', est=4)])]
        segs = {s['key']: s for s in compute_bar_segments(devs, WEIGHTS)}
        assert segs['blocked']['tickets'] == 1

    def test_in_progress_lands_in_active_bucket(self):
        devs = [_dev(tickets=[_ticket(status='In Progress', est=8)])]
        segs = {s['key']: s for s in compute_bar_segments(devs, WEIGHTS)}
        assert segs['active']['tickets'] == 1

    def test_pct_sums_to_100_when_all_estimated(self):
        devs = [_dev(tickets=[
            _ticket('ECD-1', 'Done', est=4),
            _ticket('ECD-2', 'Blocked', est=4),
            _ticket('ECD-3', 'In Progress', est=4),
            _ticket('ECD-4', 'Ready for Dev', est=4),
        ])]
        segs = compute_bar_segments(devs, WEIGHTS)
        total_pct = sum(s['pct'] for s in segs)
        assert total_pct == pytest.approx(100.0, abs=0.5)

    def test_empty_developers_all_zeros(self):
        segs = {s['key']: s for s in compute_bar_segments([], WEIGHTS)}
        assert all(s['tickets'] == 0 for s in segs.values())


# ── compute_why_behind ────────────────────────────────────────────────────────

class TestComputeWhyBehind:
    def test_no_issues_returns_empty(self):
        devs = [_dev(tickets=[_ticket(status='In Progress', est=8, logged=4)])]
        reasons = compute_why_behind(devs, WEIGHTS, biz_days_left=5)
        assert reasons == []

    def test_blocked_ticket_appears(self):
        devs = [_dev(tickets=[_ticket(status='Blocked')])]
        reasons = compute_why_behind(devs, WEIGHTS, biz_days_left=5)
        assert any('blocked' in r.lower() for r in reasons)

    def test_overdue_ticket_appears(self):
        devs = [_dev(tickets=[_ticket(due=_days_ago(1), status='In Progress')])]
        reasons = compute_why_behind(devs, WEIGHTS, biz_days_left=5)
        assert any('overdue' in r.lower() for r in reasons)

    def test_overloaded_dev_appears(self):
        # 200h remaining, only 5 days * 6h = 30h available → ratio > 1.2
        devs = [_dev(tickets=[_ticket(status='In Progress', est=200, logged=0)])]
        reasons = compute_why_behind(devs, WEIGHTS, biz_days_left=5)
        assert any('overloaded' in r.lower() or 'capacity' in r.lower() for r in reasons)

    def test_plural_blocked_label(self):
        devs = [_dev(tickets=[
            _ticket('ECD-1', 'Blocked'),
            _ticket('ECD-2', 'Blocked'),
        ])]
        reasons = compute_why_behind(devs, WEIGHTS, biz_days_left=5)
        blocked_reason = next(r for r in reasons if 'blocked' in r.lower())
        assert '2' in blocked_reason


# ── compute_action_items ──────────────────────────────────────────────────────

class TestComputeActionItems:
    def test_blocked_ticket_is_critical(self):
        devs = [_dev(tickets=[_ticket('ECD-1', 'Blocked')])]
        items = compute_action_items(devs, WEIGHTS)
        assert len(items) == 1
        assert items[0]['severity'] == 'critical'
        assert items[0]['type'] == 'blocked'
        assert items[0]['ticket'] == 'ECD-1'

    def test_overdue_ticket_is_critical(self):
        devs = [_dev(tickets=[_ticket('ECD-1', 'In Progress', due=_days_ago(1))])]
        items = compute_action_items(devs, WEIGHTS)
        assert any(i['type'] == 'overdue' and i['severity'] == 'critical' for i in items)

    def test_done_ticket_not_in_action_items(self):
        devs = [_dev(tickets=[_ticket('ECD-1', 'Done', due=_days_ago(5))])]
        items = compute_action_items(devs, WEIGHTS)
        assert len(items) == 0

    def test_sorted_critical_before_warning(self):
        # Changes requested = warning (sw 0.50–0.65 — use In QA at 0.85, that's qa not changes)
        # Need a status with sw between 0.50 and 0.65 — not in our default WEIGHTS
        # Let's use a custom weight map
        w = {**WEIGHTS, 'Changes Requested': 0.60}
        devs = [_dev(tickets=[
            _ticket('ECD-1', 'Changes Requested', due=_days_ahead(3)),
            _ticket('ECD-2', 'Blocked'),
        ])]
        items = compute_action_items(devs, w)
        # Blocked (critical) should come before Changes Requested (warning)
        critical_idx = next(i for i, x in enumerate(items) if x['severity'] == 'critical')
        warning_idx  = next(i for i, x in enumerate(items) if x['severity'] == 'warning')
        assert critical_idx < warning_idx

    def test_dev_name_included(self):
        devs = [_dev('Charlie', tickets=[_ticket('ECD-1', 'Blocked')])]
        items = compute_action_items(devs, WEIGHTS)
        assert items[0]['dev'] == 'Charlie'


# ── compute_dev_projections ───────────────────────────────────────────────────

class TestComputeDevProjections:
    def test_overdue_ticket_is_critical(self):
        dev = _dev(tickets=[_ticket('ECD-1', 'In Progress', est=8, logged=2,
                                    due=_days_ago(1))])
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=3)
        assert projs[0]['risk'] == 'critical'
        assert projs[0]['projection'] == 'OVERDUE'

    def test_at_risk_when_insufficient_time(self):
        # 20h remaining, only 6h to deadline (1 biz day)
        dev = _dev(tickets=[_ticket('ECD-1', 'In Progress', est=20, logged=0,
                                    due=_days_ahead(1))])
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=5)
        at_risk = next((p for p in projs if p['key'] == 'ECD-1'), None)
        assert at_risk is not None
        assert at_risk['risk'] in ('critical', 'warning')

    def test_done_ticket_excluded(self):
        dev = _dev(tickets=[
            _ticket('ECD-1', 'Done', est=8, logged=8),
            _ticket('ECD-2', 'In Progress', est=4, logged=0),
        ])
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=5)
        keys = [p['key'] for p in projs]
        assert 'ECD-1' not in keys
        assert 'ECD-2' in keys

    def test_on_track_ticket(self):
        # Dev has a heavy overall workload (so hours_per_day is capped at 6),
        # and one small ticket that needs only ~0.3 days — clearly on track.
        # hours_per_day = min(50h / 8 days, 6) = 6h/day
        # days_needed for the small ticket = 2h / 6h/day = 0.33 → well below 0.8*8=6.4
        tickets = [_ticket(f'ECD-{i}', 'In Progress', est=6, logged=0)
                   for i in range(8)]  # 48h total
        tickets.append(_ticket('ECD-small', 'In Progress', est=2, logged=0,
                               due=_days_ahead(10)))
        dev = _dev(tickets=tickets)
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=8)
        small = next(p for p in projs if p['key'] == 'ECD-small')
        assert small['risk'] == 'none'
        assert small['projection'] == 'On Track'

    def test_sorted_critical_first(self):
        dev = _dev(tickets=[
            _ticket('ECD-1', 'In Progress', est=4, logged=0, due=_days_ahead(10)),
            _ticket('ECD-2', 'In Progress', est=4, logged=0, due=_days_ago(1)),
        ])
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=5)
        assert projs[0]['risk'] == 'critical'

    def test_remaining_hours_computed_correctly(self):
        dev = _dev(tickets=[_ticket('ECD-1', 'In Progress', est=10, logged=3)])
        projs = compute_dev_projections(dev, WEIGHTS, biz_days_left=5)
        assert projs[0]['remaining_hours'] == pytest.approx(7.0)


# ── compute_performance_devs ──────────────────────────────────────────────────

class TestComputePerformanceDev:
    def _team(self, jira_id='alice', name='Alice', role='dev', wk_cap=40):
        return [{
            'is_active': True, 'role': role,
            'jira_account_id': jira_id, 'display_name': name,
            'weekly_capacity_hours': wk_cap,
        }]

    def _sprint_params(self, start_offset=-5, end_offset=5):
        start = (date.today() + timedelta(days=start_offset)).isoformat()
        end   = (date.today() + timedelta(days=end_offset)).isoformat()
        total = biz_days(start, end)
        elapsed = biz_days(start, date.today().isoformat())
        days_left = biz_days(date.today().isoformat(), end)
        pct = min(elapsed / total, 1.0) if total > 0 else 0.0
        return days_left, total, pct, 2.0  # days_left, total_biz, pct_elapsed, sprint_weeks

    def test_on_track_dev(self):
        start = (date.today() - timedelta(days=5)).isoformat()
        end   = (date.today() + timedelta(days=5)).isoformat()
        total = biz_days(start, end)
        elapsed = biz_days(start, date.today().isoformat())
        pct = min(elapsed / total, 1.0) if total > 0 else 0.0
        days_left = biz_days(date.today().isoformat(), end)

        # Dev has completed pct_elapsed fraction → on track
        done_est = round(pct * 40)
        todo_est = 40 - done_est
        tickets = ([_ticket(f'ECD-{i}', 'Done', est=1) for i in range(done_est)] +
                   [_ticket(f'ECD-{100+i}', 'In Progress', est=1) for i in range(todo_est)])

        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': tickets}]
        result = compute_performance_devs(
            devs_raw, WEIGHTS, self._team(), days_left, total, pct, 2.0
        )
        assert len(result) == 1
        assert result[0]['velocity_status'] in ('on_track', 'ahead')

    def test_no_tickets_dev(self):
        days_left, total, pct, sw = self._sprint_params()
        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': []}]
        result = compute_performance_devs(
            devs_raw, WEIGHTS, self._team(), days_left, total, pct, sw
        )
        assert result[0]['velocity_status'] == 'no_tickets'

    def test_overloaded_dev(self):
        days_left, total, pct, sw = self._sprint_params()
        # 200h assigned to a 40h/week 2-week (80h capacity) dev → overloaded
        tickets = [_ticket(f'ECD-{i}', 'In Progress', est=20) for i in range(10)]
        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': tickets}]
        result = compute_performance_devs(
            devs_raw, WEIGHTS, self._team(), days_left, total, pct, sw
        )
        assert result[0]['velocity_status'] == 'overloaded'

    def test_inactive_member_excluded(self):
        days_left, total, pct, sw = self._sprint_params()
        team = [{'is_active': False, 'role': 'dev', 'jira_account_id': 'alice',
                 'display_name': 'Alice', 'weekly_capacity_hours': 40}]
        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': []}]
        result = compute_performance_devs(devs_raw, WEIGHTS, team, days_left, total, pct, sw)
        assert len(result) == 0

    def test_pm_role_excluded(self):
        days_left, total, pct, sw = self._sprint_params()
        team = self._team(role='pm')
        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': []}]
        result = compute_performance_devs(devs_raw, WEIGHTS, team, days_left, total, pct, sw)
        assert len(result) == 0

    def test_design_team_included_with_wa_role(self):
        days_left, total, pct, sw = self._sprint_params()
        team = self._team(role='wa', name='Dana Designer')
        devs_raw = [{'account_id': 'alice', 'name': 'Dana Designer', 'tickets': []}]
        result = compute_performance_devs(devs_raw, WEIGHTS, team, days_left, total, pct, sw)
        assert len(result) == 1

    def test_result_includes_required_keys(self):
        days_left, total, pct, sw = self._sprint_params()
        devs_raw = [{'account_id': 'alice', 'name': 'Alice', 'tickets': []}]
        result = compute_performance_devs(
            devs_raw, WEIGHTS, self._team(), days_left, total, pct, sw
        )
        r = result[0]
        for key in ('name', 'role', 'velocity_status', 'velocity_label',
                    'actual_done_pct', 'ideal_done_pct', 'gap',
                    'capacity_hours', 'health_score', 'ticket_summary',
                    'health_reasons', 'tickets_at_risk', 'all_projections'):
            assert key in r, f"Missing key: {key}"


# ── compute_planning_summary ──────────────────────────────────────────────────

class TestComputePlanningSummary:
    def _planning(self, devs=None, unassigned=None):
        return {
            'sprint': {'name': 'Sprint 25', 'start_date': '2026-03-24', 'end_date': '2026-04-04'},
            'developers': devs or [],
            'unassigned_tickets': unassigned or [],
            'rollover_context': None,
        }

    def _dev(self, name='Alice', role='dev', cap=80, planned=60, rollover=0):
        return {
            'display_name': name, 'role': role,
            'capacity_hours': cap,
            'planned_hours': planned,
            'rollover_hours': rollover,
            'total_load_hours': planned + rollover,
        }

    def test_returns_none_for_empty_input(self):
        assert compute_planning_summary(None) is None
        assert compute_planning_summary({}) is None

    def test_totals_calculated_correctly(self):
        planning = self._planning(devs=[
            self._dev('Alice', cap=80, planned=60, rollover=10),
            self._dev('Bob',   cap=80, planned=70, rollover=5),
        ])
        result = compute_planning_summary(planning)
        assert result['total_capacity_hours'] == 160.0
        assert result['total_planned_hours'] == 130.0
        assert result['rollover_hours'] == 15.0
        assert result['total_load_hours'] == 145.0

    def test_healthy_status(self):
        planning = self._planning(devs=[self._dev(cap=80, planned=60)])
        result = compute_planning_summary(planning)
        assert result['status'] == 'Healthy'
        assert result['load_pct'] == 75

    def test_tight_status(self):
        planning = self._planning(devs=[self._dev(cap=80, planned=72)])
        result = compute_planning_summary(planning)
        assert result['status'] == 'Tight'

    def test_overloaded_status(self):
        planning = self._planning(devs=[self._dev(cap=80, planned=90)])
        result = compute_planning_summary(planning)
        assert result['status'] == 'Overloaded'

    def test_per_dev_buffer(self):
        planning = self._planning(devs=[self._dev(cap=80, planned=60)])
        result = compute_planning_summary(planning)
        assert result['developers'][0]['buffer_hours'] == pytest.approx(20.0)

    def test_unassigned_tickets_counted(self):
        unassigned = [
            {'key': 'ECD-99', 'estimate_hours': 8},
            {'key': 'ECD-100', 'estimate_hours': 4},
        ]
        planning = self._planning(unassigned=unassigned)
        result = compute_planning_summary(planning)
        assert result['unassigned_tickets'] == 2
        assert result['unassigned_hours'] == 12.0


# ── build_report ──────────────────────────────────────────────────────────────

class TestBuildReport:
    """Integration-style tests for the main orchestrator."""

    def _minimal_report(self, devs=None):
        pulse = _pulse_data(devs=devs or [])
        burndown = _burndown_data()
        return build_report(pulse, burndown)

    def test_top_level_keys_present(self):
        report = self._minimal_report()
        for key in ('generated_at', 'sprint', 'health', 'burndown',
                    'action_items', 'developers', 'next_sprint'):
            assert key in report, f"Missing top-level key: {key}"

    def test_sprint_block_keys(self):
        report = self._minimal_report()
        for key in ('name', 'start_date', 'end_date', 'days_elapsed',
                    'total_business_days', 'days_remaining', 'pct_elapsed'):
            assert key in report['sprint']

    def test_health_block_keys(self):
        report = self._minimal_report()
        for key in ('score', 'grade', 'color', 'status_distribution', 'why_behind'):
            assert key in report['health']

    def test_burndown_block_keys(self):
        report = self._minimal_report()
        for key in ('total_hours', 'complete_pct', 'remaining_hours',
                    'ideal_hours_now', 'behind_hours', 'scope_added_hours'):
            assert key in report['burndown']

    def test_pct_elapsed_between_0_and_100(self):
        report = self._minimal_report()
        assert 0 <= report['sprint']['pct_elapsed'] <= 100

    def test_days_remaining_non_negative(self):
        report = self._minimal_report()
        assert report['sprint']['days_remaining'] >= 0

    def test_health_score_between_0_and_100(self):
        devs = [_dev(tickets=[_ticket('ECD-1', 'In Progress', est=8, logged=2)])]
        report = self._minimal_report(devs=devs)
        assert 0 <= report['health']['score'] <= 100

    def test_all_done_sprint_health_is_100(self):
        devs = [_dev(tickets=[_ticket('ECD-1', 'Done', est=8, logged=8)])]
        report = self._minimal_report(devs=devs)
        assert report['health']['score'] == 100
        assert report['health']['grade'] == 'Healthy'

    def test_status_distribution_has_five_buckets(self):
        report = self._minimal_report()
        assert set(report['health']['status_distribution'].keys()) == {
            'done', 'qa', 'active', 'todo', 'blocked'
        }

    def test_developers_empty_without_team_members(self):
        # Without team_members, velocity classification is skipped
        devs = [_dev(tickets=[_ticket()])]
        report = self._minimal_report(devs=devs)
        assert report['developers'] == []

    def test_developers_populated_with_team_members(self):
        pulse = _pulse_data(devs=[_dev('Alice', 'alice123', tickets=[_ticket()])])
        burndown = _burndown_data()
        team = [{'is_active': True, 'role': 'dev', 'jira_account_id': 'alice123',
                 'display_name': 'Alice', 'weekly_capacity_hours': 40}]
        report = build_report(pulse, burndown, team_members=team)
        assert len(report['developers']) == 1
        assert report['developers'][0]['name'] == 'Alice'

    def test_planning_summary_included_when_provided(self):
        pulse = _pulse_data()
        burndown = _burndown_data()
        planning = {
            'sprint': {'name': 'Sprint 25', 'start_date': '2026-03-24', 'end_date': '2026-04-04'},
            'developers': [{'display_name': 'Alice', 'role': 'dev',
                            'capacity_hours': 80, 'planned_hours': 60,
                            'rollover_hours': 0, 'total_load_hours': 60}],
            'unassigned_tickets': [],
            'rollover_context': None,
        }
        report = build_report(pulse, burndown, planning_data=planning)
        assert report['next_sprint'] is not None
        assert report['next_sprint']['sprint_name'] == 'Sprint 25'

    def test_next_sprint_none_when_not_provided(self):
        report = self._minimal_report()
        assert report['next_sprint'] is None

    def test_burndown_data_passed_through(self):
        pulse = _pulse_data()
        burndown = _burndown_data(behind=7.5, complete_pct=40.0)
        report = build_report(pulse, burndown)
        assert report['burndown']['behind_hours'] == 7.5
        assert report['burndown']['complete_pct'] == 40.0

    def test_jira_url_included(self):
        pulse = _pulse_data()
        pulse['jira_url'] = 'https://mycompany.atlassian.net'
        report = build_report(pulse, _burndown_data())
        assert report['jira_url'] == 'https://mycompany.atlassian.net'

    def test_action_items_for_blocked_ticket(self):
        devs = [_dev('Bob', 'bob1', tickets=[_ticket('ECD-5', 'Blocked')])]
        pulse = _pulse_data(devs=devs)
        report = build_report(pulse, _burndown_data())
        assert len(report['action_items']) >= 1
        assert report['action_items'][0]['type'] == 'blocked'

    def test_sprint_timing_with_ended_sprint(self):
        # Sprint that ended yesterday
        sprint = {
            'name': 'Old Sprint',
            'start_date': (date.today() - timedelta(days=14)).isoformat(),
            'end_date':   (date.today() - timedelta(days=1)).isoformat(),
        }
        pulse = _pulse_data(sprint=sprint)
        report = build_report(pulse, _burndown_data())
        assert report['sprint']['days_remaining'] == 0
        assert report['sprint']['pct_elapsed'] == 100
