"""
Test comment operations for Jira issues.
"""

import pytest


class TestCommentOperations:
    """Tests for adding and reading comments."""

    def test_add_simple_comment(self, jira_client, test_issue):
        """Test adding a simple text comment."""
        issue_key = test_issue['key']
        comment_text = "This is a test comment from pytest"

        result = jira_client.add_comment(issue_key, comment_text)

        assert 'id' in result
        assert 'body' in result

        # Verify comment appears in issue
        issue = jira_client.get_issue(issue_key)
        # Note: Need to expand comments to see them
        comments_url = f"issue/{issue_key}/comment"
        response = jira_client._request("GET", comments_url)
        response.raise_for_status()
        comments_data = response.json()

        assert comments_data['total'] >= 1

    def test_add_comment_with_mention(self, jira_client, test_issue):
        """Test adding a comment with user mention."""
        issue_key = test_issue['key']
        comment_text = "Mentioning a user in this comment"

        # First, find a user to mention (use the service account itself)
        myself_response = jira_client._request("GET", "myself")
        myself_response.raise_for_status()
        my_account_id = myself_response.json()['accountId']

        result = jira_client.add_comment(
            issue_key,
            comment_text,
            mention_users=[my_account_id]
        )

        assert 'id' in result

    def test_add_multiple_comments(self, jira_client, test_issue):
        """Test adding multiple comments to an issue."""
        issue_key = test_issue['key']

        comments = [
            "First comment",
            "Second comment",
            "Third comment"
        ]

        for comment_text in comments:
            result = jira_client.add_comment(issue_key, comment_text)
            assert 'id' in result

        # Verify all comments exist
        comments_url = f"issue/{issue_key}/comment"
        response = jira_client._request("GET", comments_url)
        response.raise_for_status()
        comments_data = response.json()

        assert comments_data['total'] >= len(comments)

    def test_read_comments(self, jira_client, test_issue):
        """Test reading all comments from an issue."""
        issue_key = test_issue['key']

        # Add a known comment
        test_comment = "Test comment for reading"
        jira_client.add_comment(issue_key, test_comment)

        # Read comments
        comments_url = f"issue/{issue_key}/comment"
        response = jira_client._request("GET", comments_url)
        response.raise_for_status()
        comments_data = response.json()

        assert 'comments' in comments_data
        assert len(comments_data['comments']) > 0

        # Verify our comment is there
        comment_bodies = []
        for comment in comments_data['comments']:
            body = comment.get('body', {})
            if body and 'content' in body:
                # Extract text from ADF format
                for content_block in body['content']:
                    if content_block.get('type') == 'paragraph':
                        for item in content_block.get('content', []):
                            if item.get('type') == 'text':
                                comment_bodies.append(item.get('text', ''))

        assert test_comment in comment_bodies

    def test_update_comment(self, jira_client, test_issue):
        """Test updating an existing comment."""
        issue_key = test_issue['key']

        # Add initial comment
        original_text = "Original comment text"
        result = jira_client.add_comment(issue_key, original_text)
        comment_id = result['id']

        # Update the comment
        updated_text = "Updated comment text"
        update_payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": updated_text}]
                    }
                ]
            }
        }

        update_url = f"issue/{issue_key}/comment/{comment_id}"
        response = jira_client._request("PUT", update_url, json=update_payload)
        response.raise_for_status()

        # Verify update
        get_response = jira_client._request("GET", update_url)
        get_response.raise_for_status()
        comment_data = get_response.json()

        # Extract text from updated comment
        body_text = ""
        for content_block in comment_data['body']['content']:
            if content_block.get('type') == 'paragraph':
                for item in content_block.get('content', []):
                    if item.get('type') == 'text':
                        body_text = item.get('text', '')

        assert body_text == updated_text

    def test_delete_comment(self, jira_client, test_issue):
        """Test deleting a comment."""
        issue_key = test_issue['key']

        # Add comment
        result = jira_client.add_comment(issue_key, "Comment to be deleted")
        comment_id = result['id']

        # Delete comment
        delete_url = f"issue/{issue_key}/comment/{comment_id}"
        response = jira_client._request("DELETE", delete_url)
        assert response.status_code == 204

        # Verify deletion
        get_response = jira_client._request("GET", delete_url)
        assert get_response.status_code == 404
