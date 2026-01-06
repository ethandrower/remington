"""
Jira API Client Library
Extracted from jira-cli for testing and reusability.
"""

import requests
from base64 import b64encode
from typing import Optional, Dict, Any, List


class JiraClient:
    """Jira API client for REST operations."""

    def __init__(self, email: str, token: str, cloud_id: str):
        self.email = email
        self.token = token
        self.cloud_id = cloud_id
        self.base_url = "https://citemed.atlassian.net/rest/api/3"

        # Create Basic Auth header
        auth_str = f"{email}:{token}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = b64encode(auth_bytes).decode('ascii')

        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Jira API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        return response

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get issue details."""
        response = self._request("GET", f"issue/{issue_key}")
        response.raise_for_status()
        return response.json()

    def search_issues(self, jql: str, fields: Optional[List[str]] = None, max_results: int = 50) -> Dict[str, Any]:
        """Search issues using JQL."""
        params = {
            "jql": jql,
            "maxResults": max_results
        }
        if fields:
            params["fields"] = ",".join(fields)

        response = self._request("POST", "search/jql", json=params)
        response.raise_for_status()
        return response.json()

    def create_issue(self, project_key: str, issue_type: str, summary: str,
                    description: Optional[str] = None, **extra_fields) -> Dict[str, Any]:
        """Create a new issue."""
        fields = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary
        }

        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }

        # Add extra fields
        fields.update(extra_fields)

        payload = {"fields": fields}
        response = self._request("POST", "issue", json=payload)
        response.raise_for_status()
        return response.json()

    def create_subtask(self, parent_key: str, summary: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a subtask under a parent issue."""
        # Get parent to determine project
        parent = self.get_issue(parent_key)
        project_key = parent['fields']['project']['key']

        fields = {
            "project": {"key": project_key},
            "parent": {"key": parent_key},
            "issuetype": {"name": "Sub-task"},
            "summary": summary
        }

        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }

        payload = {"fields": fields}
        response = self._request("POST", "issue", json=payload)
        response.raise_for_status()
        return response.json()

    def update_issue(self, issue_key: str, **fields) -> None:
        """Update issue fields."""
        payload = {"fields": fields}
        response = self._request("PUT", f"issue/{issue_key}", json=payload)
        response.raise_for_status()

    def add_comment(self, issue_key: str, comment_text: str, mention_users: Optional[List[str]] = None) -> Dict[str, Any]:
        """Add a comment to an issue."""
        content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": comment_text}]
            }
        ]

        # Add user mentions if provided
        if mention_users:
            for user_id in mention_users:
                content.insert(0, {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "mention",
                            "attrs": {"id": user_id}
                        }
                    ]
                })

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": content
            }
        }

        response = self._request("POST", f"issue/{issue_key}/comment", json=payload)
        response.raise_for_status()
        return response.json()

    def transition_issue(self, issue_key: str, transition_name: str) -> None:
        """Transition issue to a new status."""
        # Get available transitions
        response = self._request("GET", f"issue/{issue_key}/transitions")
        response.raise_for_status()
        transitions = response.json()['transitions']

        # Find matching transition
        transition_id = None
        for trans in transitions:
            if trans['name'].lower() == transition_name.lower():
                transition_id = trans['id']
                break

        if not transition_id:
            available = [t['name'] for t in transitions]
            raise ValueError(f"Transition '{transition_name}' not found. Available: {available}")

        # Execute transition
        payload = {"transition": {"id": transition_id}}
        response = self._request("POST", f"issue/{issue_key}/transitions", json=payload)
        response.raise_for_status()

    def search_users(self, query: str) -> List[Dict[str, Any]]:
        """Search for users by email or name."""
        response = self._request("GET", f"user/search?query={query}")
        response.raise_for_status()
        return response.json()

    def get_project(self, project_key: str) -> Dict[str, Any]:
        """Get project details."""
        response = self._request("GET", f"project/{project_key}")
        response.raise_for_status()
        return response.json()
