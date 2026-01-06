#!/usr/bin/env python3
"""
Jira REST API Client for Standup Workflows

Provides simplified interface for querying Jira data without MCP.
Used by standup_workflow.py and other automation scripts.
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import base64


class JiraAPIClient:
    """Jira REST API client using service account credentials"""

    def __init__(self):
        """Initialize with credentials from environment"""
        self.token = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.email = os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")

        if not all([self.token, self.email]):
            raise ValueError("Missing required Atlassian credentials in .env")

        # Use standard Jira Cloud URL (citemed.atlassian.net)
        self.base_url = "https://citemed.atlassian.net"
        self.auth_header = self._create_auth_header()

    def _create_auth_header(self) -> Dict[str, str]:
        """Create Basic Auth header"""
        credentials = f"{self.email}:{self.token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def search_jql(
        self,
        jql: str,
        fields: List[str] = None,
        max_results: int = 100,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Execute JQL query and return results

        Args:
            jql: JQL query string
            fields: List of fields to include (default: all)
            max_results: Maximum results to return
            start_at: Pagination offset

        Returns:
            API response with issues array
        """
        if fields is None:
            fields = ["summary", "status", "assignee", "priority", "issuetype", "updated", "created"]

        url = f"{self.base_url}/rest/api/3/search"
        payload = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
            "startAt": start_at
        }

        try:
            response = requests.post(url, headers=self.auth_header, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Jira API error: {e}")
            return {"issues": [], "total": 0, "error": str(e)}

    def get_open_sprint_issues(self, project_key: str = "ECD") -> List[Dict[str, Any]]:
        """Get all issues in currently open sprints"""
        jql = f"project = {project_key} AND sprint in openSprints() ORDER BY priority DESC, updated DESC"
        result = self.search_jql(
            jql=jql,
            fields=["summary", "status", "assignee", "priority", "issuetype", "updated", "customfield_10020"]
        )
        return result.get("issues", [])

    def get_in_progress_issues(self, project_key: str = "ECD") -> List[Dict[str, Any]]:
        """Get all issues currently In Progress"""
        jql = f'project = {project_key} AND status = "In Progress" AND sprint in openSprints() ORDER BY updated ASC'
        result = self.search_jql(
            jql=jql,
            fields=["summary", "assignee", "updated", "created"]
        )
        return result.get("issues", [])

    def get_recent_completed_issues(self, days: int = 7, project_key: str = "ECD") -> List[Dict[str, Any]]:
        """Get issues completed in the last N days"""
        date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        jql = f'project = {project_key} AND status = Done AND resolved >= "{date_threshold}" ORDER BY resolved DESC'
        result = self.search_jql(
            jql=jql,
            fields=["summary", "assignee", "resolved", "resolutiondate"]
        )
        return result.get("issues", [])

    def get_issue_by_key(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """Get single issue by key"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        try:
            response = requests.get(url, headers=self.auth_header, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching {issue_key}: {e}")
            return None

    def get_user_display_name(self, account_id: str) -> str:
        """Get user display name from account ID"""
        url = f"{self.base_url}/rest/api/3/user"
        params = {"accountId": account_id}
        try:
            response = requests.get(url, headers=self.auth_header, params=params, timeout=10)
            response.raise_for_status()
            user = response.json()
            return user.get("displayName", "Unknown")
        except requests.exceptions.RequestException:
            return "Unknown"


def format_issue_summary(issue: Dict[str, Any]) -> str:
    """Format issue as single-line summary"""
    key = issue.get("key", "???")
    fields = issue.get("fields", {})
    summary = fields.get("summary", "No summary")
    status = fields.get("status", {}).get("name", "Unknown")

    assignee = fields.get("assignee")
    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"

    return f"{key}: {summary} [{status}] - {assignee_name}"


def group_issues_by_status(issues: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group issues by their status category"""
    grouped = {}
    for issue in issues:
        status = issue.get("fields", {}).get("status", {}).get("name", "Unknown")
        if status not in grouped:
            grouped[status] = []
        grouped[status].append(issue)
    return grouped


def calculate_sprint_completion(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate sprint completion metrics"""
    if not issues:
        return {
            "total": 0,
            "done": 0,
            "in_progress": 0,
            "to_do": 0,
            "completion_pct": 0,
            "at_risk": False
        }

    done_count = sum(1 for i in issues if i.get("fields", {}).get("status", {}).get("name") == "Done")
    in_progress_count = sum(1 for i in issues if i.get("fields", {}).get("status", {}).get("name") == "In Progress")
    to_do_count = len(issues) - done_count - in_progress_count

    completion_pct = (done_count / len(issues)) * 100 if issues else 0

    # Simple risk assessment: < 50% done and < 3 days left (would need sprint end date)
    at_risk = completion_pct < 50 and in_progress_count > done_count

    return {
        "total": len(issues),
        "done": done_count,
        "in_progress": in_progress_count,
        "to_do": to_do_count,
        "completion_pct": round(completion_pct, 1),
        "at_risk": at_risk
    }


if __name__ == "__main__":
    # Quick test
    from dotenv import load_dotenv
    load_dotenv()

    client = JiraAPIClient()
    print("Testing Jira API Client...\n")

    print("📊 Fetching open sprint issues...")
    issues = client.get_open_sprint_issues()
    print(f"   Found {len(issues)} issues in open sprints\n")

    print("📈 Sprint Completion Metrics:")
    metrics = calculate_sprint_completion(issues)
    print(f"   Total: {metrics['total']}")
    print(f"   Done: {metrics['done']}")
    print(f"   In Progress: {metrics['in_progress']}")
    print(f"   To Do: {metrics['to_do']}")
    print(f"   Completion: {metrics['completion_pct']}%")
    print(f"   At Risk: {'⚠️ YES' if metrics['at_risk'] else '✅ NO'}")
