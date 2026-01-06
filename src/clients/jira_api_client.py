"""
Jira API Client - Direct API calls (no MCP needed)
Uses Atlassian REST API v3 with Basic Auth
"""
import requests
import os
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class JiraAPIClient:
    """
    Direct Jira API client
    Uses email + API token for authentication
    """

    def __init__(self):
        # Get credentials from environment
        self.email = os.getenv("ATLASSIAN_EMAIL") or os.getenv("ATLASSIAN_SERVICE_ACCOUNT_EMAIL")
        self.token = os.getenv("ATLASSIAN_API_TOKEN") or os.getenv("ATLASSIAN_SERVICE_ACCOUNT_TOKEN")
        self.domain = os.getenv("ATLASSIAN_DOMAIN", "citemed.atlassian.net")

        if not self.email or not self.token:
            raise ValueError(
                "Missing Atlassian credentials! Set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN in .env"
            )

        self.base_url = f"https://{self.domain}"
        self.auth = (self.email, self.token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_issue(self, issue_key: str) -> Dict:
        """
        Get issue by key (e.g., "ECD-123")
        Returns cleaned issue data
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers,
            params={"expand": "changelog"}  # Include change history
        )
        response.raise_for_status()

        raw = response.json()
        return self._parse_issue(raw)

    def search_issues(self, jql: str, max_results: int = 50) -> List[Dict]:
        """
        Search issues using JQL (Jira Query Language)

        Example JQL:
        - "project = ECD AND status = 'In Progress'"
        - "assignee = currentUser()"
        - "created >= -7d"
        """
        url = f"{self.base_url}/rest/api/3/search"

        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers,
            params={"jql": jql, "maxResults": max_results}
        )
        response.raise_for_status()

        data = response.json()
        issues = data.get("issues", [])

        return [self._parse_issue(issue) for issue in issues]

    def add_comment(self, issue_key: str, comment_text: str) -> Dict:
        """
        Add comment to issue
        Uses Atlassian Document Format (ADF) for rich text
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"

        # Convert plain text to ADF format
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment_text
                            }
                        ]
                    }
                ]
            }
        }

        response = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()

        return response.json()

    def get_comments(self, issue_key: str) -> List[Dict]:
        """Get all comments for an issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"

        response = requests.get(
            url,
            auth=self.auth,
            headers=self.headers
        )
        response.raise_for_status()

        data = response.json()
        comments = data.get("comments", [])

        return [
            {
                "id": c["id"],
                "author": c["author"]["displayName"],
                "body": self._extract_text_from_adf(c.get("body")),
                "created": c["created"],
                "updated": c.get("updated")
            }
            for c in comments
        ]

    def _parse_issue(self, raw: Dict) -> Dict:
        """Parse Jira API response into cleaner format"""
        fields = raw.get("fields", {})

        return {
            "key": raw.get("key"),
            "id": raw.get("id"),
            "summary": fields.get("summary"),
            "description": self._extract_text_from_adf(fields.get("description")),
            "status": fields.get("status", {}).get("name"),
            "assignee": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else "Unassigned",
            "reporter": fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
            "priority": fields.get("priority", {}).get("name"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "labels": fields.get("labels", []),
            "components": [c["name"] for c in fields.get("components", [])],
            "issue_type": fields.get("issuetype", {}).get("name"),
        }

    def _extract_text_from_adf(self, adf_content) -> Optional[str]:
        """
        Extract plain text from Atlassian Document Format (ADF)
        ADF is a complex nested JSON structure for rich text
        """
        if not adf_content:
            return None

        def extract_text(node):
            """Recursively extract text from ADF nodes"""
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                elif "content" in node:
                    return " ".join(extract_text(child) for child in node["content"])
            elif isinstance(node, list):
                return " ".join(extract_text(item) for item in node)
            return ""

        text = extract_text(adf_content)
        return text.strip() if text else None

    def test_connection(self) -> Dict:
        """
        Test API connection
        Returns user info if successful
        """
        url = f"{self.base_url}/rest/api/3/myself"

        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            user = response.json()
            return {
                "status": "success",
                "user": user.get("displayName"),
                "email": user.get("emailAddress"),
                "account_id": user.get("accountId")
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e)
            }


if __name__ == "__main__":
    """
    Test the Jira client
    Run: python src/clients/jira_api_client.py
    """
    print("\n🧪 Testing Jira API Client...\n")

    try:
        client = JiraAPIClient()

        # Test 1: Connection
        print("Test 1: Testing connection...")
        result = client.test_connection()
        if result["status"] == "success":
            print(f"✅ Connected as: {result['user']} ({result['email']})")
        else:
            print(f"❌ Connection failed: {result['error']}")
            exit(1)

        # Test 2: Search for recent issues
        print("\nTest 2: Searching for recent ECD issues...")
        issues = client.search_issues("project = ECD ORDER BY created DESC", max_results=5)
        print(f"✅ Found {len(issues)} issues")
        if issues:
            print("\n   Recent issues:")
            for issue in issues[:3]:
                print(f"   - {issue['key']}: {issue['summary']} ({issue['status']})")

        print("\n✅ All tests passed!\n")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nMake sure you have these in your .env file:")
        print("  ATLASSIAN_EMAIL=your-email@example.com")
        print("  ATLASSIAN_API_TOKEN=your-api-token")
        print("  ATLASSIAN_DOMAIN=citemed.atlassian.net\n")

    except Exception as e:
        print(f"\n❌ Error: {e}\n")
