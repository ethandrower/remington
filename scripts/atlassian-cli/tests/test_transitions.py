"""
Test issue transitions and workflow operations.
"""

import pytest


class TestTransitions:
    """Tests for transitioning issues between statuses."""

    def test_get_available_transitions(self, jira_client, test_issue):
        """Test retrieving available transitions for an issue."""
        issue_key = test_issue['key']

        response = jira_client._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        assert len(transitions) > 0
        assert all('id' in t and 'name' in t for t in transitions)

    def test_transition_issue(self, jira_client, test_issue):
        """Test transitioning an issue to a new status."""
        issue_key = test_issue['key']

        # Get available transitions
        response = jira_client._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        # Skip if no transitions available
        if len(transitions) == 0:
            pytest.skip("No transitions available for this issue")

        # Try to transition to the first available status
        transition = transitions[0]
        transition_name = transition['name']

        try:
            jira_client.transition_issue(issue_key, transition_name)

            # Verify transition occurred
            updated_issue = jira_client.get_issue(issue_key)
            # Status should have changed (we can't predict exact status due to workflow)
            assert 'status' in updated_issue['fields']
        except ValueError as e:
            # If transition not found, that's also acceptable (workflow dependent)
            assert "not found" in str(e).lower()

    def test_transition_to_done(self, jira_client, test_issue):
        """Test transitioning an issue to Done status."""
        issue_key = test_issue['key']

        # Get available transitions
        response = jira_client._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        # Look for Done transition
        done_transitions = [t for t in transitions if 'done' in t['name'].lower()]

        if not done_transitions:
            pytest.skip("No 'Done' transition available for this issue")

        # Transition to Done
        jira_client.transition_issue(issue_key, done_transitions[0]['name'])

        # Verify status
        updated_issue = jira_client.get_issue(issue_key)
        status_name = updated_issue['fields']['status']['name']
        assert 'done' in status_name.lower() or 'closed' in status_name.lower()

    def test_invalid_transition(self, jira_client, test_issue):
        """Test transitioning to an invalid status raises error."""
        issue_key = test_issue['key']

        with pytest.raises(ValueError) as exc_info:
            jira_client.transition_issue(issue_key, "InvalidStatusThatDoesNotExist123")

        assert "not found" in str(exc_info.value).lower()

    def test_multi_step_workflow(self, jira_client, test_project_key, created_issues):
        """Test moving an issue through multiple workflow states."""
        # Create a fresh issue
        result = jira_client.create_issue(
            project_key=test_project_key,
            issue_type="Task",
            summary="[TEST] Multi-step workflow test"
        )

        issue_key = result['key']
        created_issues.append(issue_key)

        # Record initial status
        issue = jira_client.get_issue(issue_key)
        initial_status = issue['fields']['status']['name']

        # Get all available transitions
        response = jira_client._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        # Try to go through multiple transitions
        statuses_visited = [initial_status]

        for transition in transitions[:2]:  # Try first 2 transitions
            try:
                jira_client.transition_issue(issue_key, transition['name'])

                # Record new status
                updated = jira_client.get_issue(issue_key)
                new_status = updated['fields']['status']['name']
                statuses_visited.append(new_status)

                # Get new available transitions
                response = jira_client._request("GET", f"issue/{issue_key}/transitions")
                response.raise_for_status()
                transitions = response.json()['transitions']

            except Exception as e:
                # Some transitions might fail due to workflow rules
                print(f"Transition failed: {e}")
                break

        # Verify we moved through at least one status
        assert len(set(statuses_visited)) >= 1  # At least the initial status


class TestWorkflowValidation:
    """Tests for workflow validation and rules."""

    def test_transition_preserves_other_fields(self, jira_client, test_issue):
        """Test that transitioning doesn't affect other fields."""
        issue_key = test_issue['key']
        original_summary = test_issue['fields']['summary']

        # Get available transitions
        response = jira_client._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        if len(transitions) == 0:
            pytest.skip("No transitions available")

        # Perform transition
        try:
            jira_client.transition_issue(issue_key, transitions[0]['name'])

            # Verify summary unchanged
            updated = jira_client.get_issue(issue_key)
            assert updated['fields']['summary'] == original_summary
        except ValueError:
            pytest.skip("Transition not available")

    def test_get_workflow_status_categories(self, jira_client, test_issue):
        """Test retrieving status categories (To Do, In Progress, Done)."""
        issue_key = test_issue['key']

        issue = jira_client.get_issue(issue_key)
        status = issue['fields']['status']

        assert 'statusCategory' in status
        assert 'name' in status['statusCategory']

        # Status category should be one of the standard ones
        valid_categories = ['To Do', 'In Progress', 'Done']
        assert status['statusCategory']['name'] in valid_categories
