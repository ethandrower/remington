"""
Tests for GET /api/agent/sprint-report

Uses the Flask test client. The internal Jira fetch helpers
(_fetch_sprint_pulse_data, _fetch_sprint_burndown_data) are patched to return
pre-built dicts, keeping tests fast and hermetic.
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


# ── Shared data builders ──────────────────────────────────────────────────────

TODAY        = date.today().isoformat()
SPRINT_START = (date.today() - timedelta(days=5)).isoformat()
SPRINT_END   = (date.today() + timedelta(days=5)).isoformat()


def _default_pulse(devs=None, weights=None):
    return {
        'sprint': {
            'id': 42,
            'name': 'Sprint 24',
            'start_date': SPRINT_START,
            'end_date':   SPRINT_END,
            'state': 'active',
            'board_name': 'ECD Board',
        },
        'developers': devs or [],
        'status_weights': weights or {
            'Done':       1.0,
            'In Progress': 0.35,
            'Blocked':    0.02,
            'In QA':      0.85,
        },
        'project_key': 'ECD',
        'jira_url':    'https://example.atlassian.net',
        'last_updated': TODAY + 'T00:00:00Z',
    }


def _default_burndown(behind=2.5, complete_pct=40.0):
    return {
        'sprint': {'name': 'Sprint 24', 'start_date': SPRINT_START, 'end_date': SPRINT_END},
        'daily_snapshots': [
            {'date': TODAY, 'complete': 16.0, 'verifying': 4.0, 'active': 8.0,
             'queued': 8.0, 'blocked': 4.0, 'remaining': 24.0,
             'ideal': 24.0 - behind, 'scope': 40.0},
        ],
        'total_hours':    40.0,
        'initial_hours':  38.0,
        'added_hours':    2.0,
        'added_tickets':  1,
        'scope_additions': [{'key': 'ECD-99', 'hours': 2.0, 'added_date': TODAY}],
        'behind_hours':   behind,
        'blocked_hours':  4.0,
        'complete_hours': 16.0,
        'complete_pct':   complete_pct,
    }


def _dev(name='Alice', account_id='alice123', status='In Progress',
         est=8.0, logged=2.0, due=None):
    return {
        'account_id': account_id,
        'name': name,
        'tickets': [{
            'key': 'ECD-1',
            'summary': 'Fix login flow',
            'status': status,
            'priority': 'High',
            'estimate_hours': est,
            'logged_hours': logged,
            'due_date': due,
        }],
    }


def _team_member(jira_id='alice123', name='Alice Smith', role='dev', wk_cap=40):
    return {
        'id': 1,
        'display_name': name,
        'jira_account_id': jira_id,
        'role': role,
        'is_active': True,
        'weekly_capacity_hours': wk_cap,
    }


# ── Flask app fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch):
    """Flask test client with all external dependencies stubbed."""
    import os
    monkeypatch.setenv('ATLASSIAN_PROJECT_KEY', 'ECD')

    mock_db = MagicMock()
    mock_db.get_team_members.return_value = [_team_member()]

    with patch('trinity.base.ATLASSIAN_CLOUD_ID', 'test-cloud-id'), \
         patch('trinity.base.JIRA_WEB_URL', 'https://example.atlassian.net'), \
         patch('trinity.base.get_jira_auth_headers', return_value={}), \
         patch('src.dashboard.app.db', mock_db):
        from src.dashboard.app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c


# ── Test helper ───────────────────────────────────────────────────────────────

def _get_report(client, pulse=None, burndown=None, params='',
                pulse_raises=None, burndown_raises=None):
    """
    Call /api/agent/sprint-report with patched fetch helpers.
    Pass pulse_raises/burndown_raises to simulate fetch errors.
    """
    pulse_ret    = pulse    or _default_pulse()
    burndown_ret = burndown or _default_burndown()

    def mock_pulse(*args, **kwargs):
        if pulse_raises:
            raise pulse_raises
        return pulse_ret

    def mock_burndown(*args, **kwargs):
        if burndown_raises:
            raise burndown_raises
        return burndown_ret

    with patch('src.dashboard.app._fetch_sprint_pulse_data',    side_effect=mock_pulse), \
         patch('src.dashboard.app._fetch_sprint_burndown_data', side_effect=mock_burndown):
        return client.get(f'/api/agent/sprint-report{params}')


# ── Basic status & structure ──────────────────────────────────────────────────

class TestResponseStructure:

    def test_returns_200(self, client):
        assert _get_report(client).status_code == 200

    def test_response_is_valid_json(self, client):
        resp = _get_report(client)
        assert resp.get_json() is not None

    def test_top_level_keys_present(self, client):
        data = _get_report(client).get_json()
        for key in ('generated_at', 'sprint', 'health', 'burndown',
                    'action_items', 'developers', 'next_sprint'):
            assert key in data, f"Missing top-level key: {key}"

    def test_sprint_block_keys(self, client):
        sprint = _get_report(client).get_json()['sprint']
        for key in ('name', 'start_date', 'end_date', 'days_elapsed',
                    'total_business_days', 'days_remaining', 'pct_elapsed'):
            assert key in sprint, f"Sprint missing key: {key}"

    def test_health_block_keys(self, client):
        health = _get_report(client).get_json()['health']
        for key in ('score', 'grade', 'color', 'status_distribution', 'why_behind'):
            assert key in health, f"Health missing key: {key}"

    def test_burndown_block_keys(self, client):
        bd = _get_report(client).get_json()['burndown']
        for key in ('total_hours', 'complete_pct', 'behind_hours',
                    'scope_added_hours', 'scope_added_tickets', 'remaining_hours'):
            assert key in bd, f"Burndown missing key: {key}"

    def test_generated_at_is_iso8601_utc(self, client):
        from datetime import datetime
        ts = _get_report(client).get_json()['generated_at']
        assert ts.endswith('Z')
        datetime.fromisoformat(ts.replace('Z', '+00:00'))  # no exception = valid


# ── Sprint block content ──────────────────────────────────────────────────────

class TestSprintBlock:

    def test_sprint_name_matches_pulse(self, client):
        pulse = _default_pulse()
        pulse['sprint']['name'] = 'My Sprint'
        data = _get_report(client, pulse=pulse).get_json()
        assert data['sprint']['name'] == 'My Sprint'

    def test_dates_passed_through(self, client):
        data = _get_report(client).get_json()
        assert data['sprint']['start_date'] == SPRINT_START
        assert data['sprint']['end_date']   == SPRINT_END

    def test_pct_elapsed_between_0_and_100(self, client):
        pct = _get_report(client).get_json()['sprint']['pct_elapsed']
        assert 0 <= pct <= 100

    def test_days_remaining_non_negative(self, client):
        days = _get_report(client).get_json()['sprint']['days_remaining']
        assert days >= 0


# ── Health block ──────────────────────────────────────────────────────────────

class TestHealthBlock:

    def test_score_is_integer_in_range(self, client):
        score = _get_report(client).get_json()['health']['score']
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_grade_is_valid_label(self, client):
        grade = _get_report(client).get_json()['health']['grade']
        assert grade in ('Healthy', 'On Track', 'At Risk', 'Behind')

    def test_status_distribution_has_five_buckets(self, client):
        dist = _get_report(client).get_json()['health']['status_distribution']
        assert set(dist.keys()) == {'done', 'qa', 'active', 'todo', 'blocked'}

    def test_all_done_sprint_scores_100(self, client):
        pulse = _default_pulse(devs=[_dev(status='Done', est=8, logged=8)])
        data  = _get_report(client, pulse=pulse).get_json()
        assert data['health']['score'] == 100
        assert data['health']['grade'] == 'Healthy'

    def test_all_blocked_sprint_is_behind(self, client):
        pulse = _default_pulse(devs=[_dev(status='Blocked', est=8, logged=0)])
        data  = _get_report(client, pulse=pulse).get_json()
        assert data['health']['grade'] in ('At Risk', 'Behind')


# ── Burndown block ────────────────────────────────────────────────────────────

class TestBurndownBlock:

    def test_complete_pct_passed_through(self, client):
        bd = _default_burndown(complete_pct=55.0)
        data = _get_report(client, burndown=bd).get_json()
        assert data['burndown']['complete_pct'] == 55.0

    def test_behind_hours_passed_through(self, client):
        bd = _default_burndown(behind=8.5)
        data = _get_report(client, burndown=bd).get_json()
        assert data['burndown']['behind_hours'] == 8.5

    def test_scope_additions_included(self, client):
        data = _get_report(client).get_json()
        assert data['burndown']['scope_added_tickets'] == 1
        assert data['burndown']['scope_added_hours']   == 2.0


# ── Action items ──────────────────────────────────────────────────────────────

class TestActionItems:

    def test_blocked_ticket_is_critical_action(self, client):
        pulse = _default_pulse(devs=[_dev('Alice', 'alice123', status='Blocked')])
        items = _get_report(client, pulse=pulse).get_json()['action_items']
        assert any(i['type'] == 'blocked' and i['severity'] == 'critical'
                   for i in items)

    def test_overdue_ticket_is_critical_action(self, client):
        overdue = (date.today() - timedelta(days=2)).isoformat()
        pulse = _default_pulse(devs=[_dev(status='In Progress', due=overdue)])
        items = _get_report(client, pulse=pulse).get_json()['action_items']
        assert any(i['type'] == 'overdue' and i['severity'] == 'critical'
                   for i in items)

    def test_no_action_items_for_done_sprint(self, client):
        pulse = _default_pulse(devs=[_dev(status='Done', est=8, logged=8)])
        items = _get_report(client, pulse=pulse).get_json()['action_items']
        assert items == []

    def test_action_item_has_required_fields(self, client):
        pulse = _default_pulse(devs=[_dev(status='Blocked')])
        items = _get_report(client, pulse=pulse).get_json()['action_items']
        item = items[0]
        for key in ('severity', 'type', 'ticket', 'summary', 'dev'):
            assert key in item, f"Action item missing: {key}"


# ── Developer performance ─────────────────────────────────────────────────────

class TestDeveloperPerformance:

    def test_team_member_velocity_classified(self, client):
        pulse = _default_pulse(devs=[_dev('Alice', 'alice123')])
        devs  = _get_report(client, pulse=pulse).get_json()['developers']
        assert len(devs) == 1
        assert devs[0]['name'] == 'Alice Smith'
        assert devs[0]['velocity_status'] in (
            'on_track', 'behind', 'at_risk', 'ahead', 'overloaded', 'no_tickets'
        )

    def test_developer_has_all_required_fields(self, client):
        pulse = _default_pulse(devs=[_dev('Alice', 'alice123')])
        dev   = _get_report(client, pulse=pulse).get_json()['developers'][0]
        for key in ('name', 'role', 'velocity_status', 'velocity_label',
                    'actual_done_pct', 'ideal_done_pct', 'gap',
                    'health_score', 'ticket_summary', 'health_reasons',
                    'tickets_at_risk', 'all_projections'):
            assert key in dev, f"Developer missing key: {key}"

    def test_no_developers_when_no_sprint_tickets(self, client):
        # Team member exists but has no tickets in sprint
        pulse = _default_pulse(devs=[])
        devs  = _get_report(client, pulse=pulse).get_json()['developers']
        assert len(devs) == 1  # member still listed, velocity = no_tickets
        assert devs[0]['velocity_status'] == 'no_tickets'

    def test_ticket_summary_fields(self, client):
        pulse = _default_pulse(devs=[_dev('Alice', 'alice123', status='Done',
                                         est=8, logged=8)])
        dev = _get_report(client, pulse=pulse).get_json()['developers'][0]
        ts = dev['ticket_summary']
        for key in ('total', 'done', 'active', 'blocked', 'overdue'):
            assert key in ts


# ── Query params ──────────────────────────────────────────────────────────────

class TestQueryParams:

    def test_include_burndown_0_skips_changelog(self, client):
        """With include_burndown=0, _fetch_sprint_burndown_data should NOT be called."""
        call_count = {'n': 0}
        def track_burndown(*args, **kwargs):
            call_count['n'] += 1
            return _default_burndown()

        pulse = _default_pulse(devs=[_dev()])
        with patch('src.dashboard.app._fetch_sprint_pulse_data',
                   return_value=pulse), \
             patch('src.dashboard.app._fetch_sprint_burndown_data',
                   side_effect=track_burndown):
            resp = client.get('/api/agent/sprint-report?include_burndown=0')
        assert resp.status_code == 200
        assert call_count['n'] == 0

    def test_include_planning_0_skips_planning_fetch(self, client):
        """With include_planning=0, next_sprint should be None."""
        data = _get_report(client, params='?include_planning=0').get_json()
        assert data['next_sprint'] is None

    def test_include_burndown_1_calls_burndown(self, client):
        """Default behaviour calls burndown."""
        call_count = {'n': 0}
        def track_burndown(*args, **kwargs):
            call_count['n'] += 1
            return _default_burndown()

        pulse = _default_pulse(devs=[_dev()])
        with patch('src.dashboard.app._fetch_sprint_pulse_data',
                   return_value=pulse), \
             patch('src.dashboard.app._fetch_sprint_burndown_data',
                   side_effect=track_burndown):
            resp = client.get('/api/agent/sprint-report')
        assert resp.status_code == 200
        assert call_count['n'] == 1


# ── Error handling ────────────────────────────────────────────────────────────

class TestErrorHandling:

    def test_404_when_no_active_sprint(self, client):
        resp = _get_report(client, pulse_raises=LookupError("No active sprint found"))
        assert resp.status_code == 404
        assert 'error' in resp.get_json()

    def test_500_on_unexpected_jira_error(self, client):
        resp = _get_report(client, pulse_raises=RuntimeError("JQL search failed: 500"))
        assert resp.status_code == 500
        data = resp.get_json()
        assert 'error' in data

    def test_burndown_failure_is_non_fatal(self, client):
        """Burndown fetch failure should surface as fetch_warning, not 500."""
        resp = _get_report(client, burndown_raises=Exception("Changelog timeout"))
        # The endpoint catches burndown failures and continues
        assert resp.status_code == 200
        data = resp.get_json()
        # Should have a warning, not fail entirely
        assert 'fetch_warnings' in data or 'burndown' in data

    def test_error_response_has_error_key(self, client):
        resp = _get_report(client, pulse_raises=LookupError("No sprint"))
        assert 'error' in resp.get_json()

    def test_missing_project_key_returns_400(self, client, monkeypatch):
        monkeypatch.setenv('ATLASSIAN_PROJECT_KEY', '')
        # The endpoint checks project_key before calling any fetch helper, so
        # the 400 is returned from the route's own guard (no patch needed).
        resp = client.get('/api/agent/sprint-report')
        assert resp.status_code == 400
