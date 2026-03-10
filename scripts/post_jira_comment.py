#!/usr/bin/env python3
"""
Helper script for posting Jira comments with mentions via REST API

Usage:
    python scripts/post_jira_comment.py ECD-123 "Hello @user" --mention-id 712020:xxx --mention-name "UserName"
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bots.jira_monitor import JiraMonitor


def build_adf_with_mentions(text: str, mentions: list = None) -> list:
    """
    Build ADF content with text and mentions

    Args:
        text: Plain text (can include {mention} placeholders)
        mentions: List of dicts with 'id' and 'name' keys

    Returns:
        ADF content array
    """
    if not mentions:
        # Simple text only
        return [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }
        ]

    # Build content with mentions
    content_nodes = []
    remaining_text = text

    for mention in mentions:
        # Split text at mention placeholder or @name
        mention_name = mention['name']
        parts = remaining_text.split(f"@{mention_name}", 1)

        if len(parts) == 2:
            # Add text before mention
            if parts[0]:
                content_nodes.append({"type": "text", "text": parts[0]})

            # Add mention node
            content_nodes.append({
                "type": "mention",
                "attrs": {
                    "id": mention['id'],
                    "text": f"@{mention_name}"
                }
            })

            remaining_text = parts[1]
        else:
            # Mention not found in text, continue
            pass

    # Add any remaining text
    if remaining_text:
        content_nodes.append({"type": "text", "text": remaining_text})

    return [
        {
            "type": "paragraph",
            "content": content_nodes if content_nodes else [{"type": "text", "text": text}]
        }
    ]


def main():
    parser = argparse.ArgumentParser(description="Post Jira comment with mentions")
    parser.add_argument("issue_key", help="Jira issue key (e.g., ECD-123)")
    parser.add_argument("text", help="Comment text (use @Name for mentions)")
    parser.add_argument("--mention-id", action="append", help="Account ID for mention")
    parser.add_argument("--mention-name", action="append", help="Display name for mention")

    args = parser.parse_args()

    # Build mentions list
    mentions = []
    if args.mention_id and args.mention_name:
        if len(args.mention_id) != len(args.mention_name):
            print("ERROR: Number of --mention-id and --mention-name must match")
            sys.exit(1)

        for account_id, name in zip(args.mention_id, args.mention_name):
            mentions.append({"id": account_id, "name": name})

    # Build ADF content
    adf_content = build_adf_with_mentions(args.text, mentions)

    # Initialize Jira monitor and post comment
    try:
        monitor = JiraMonitor()
        success = monitor.add_comment_with_adf(args.issue_key, adf_content)

        if success:
            print(f"✅ Successfully posted comment to {args.issue_key}")
            sys.exit(0)
        else:
            print(f"❌ Failed to post comment to {args.issue_key}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
