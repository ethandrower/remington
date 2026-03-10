#!/usr/bin/env python3
"""
Test Claude Code MCP Integration

Tests if Claude Code can successfully query Jira via MCP tools.
"""

import subprocess
import json
import sys


def test_jira_query():
    """Test basic Jira query via Claude Code MCP"""
    print("🧪 Testing Claude Code MCP - Jira Query\n")

    prompt = """Use the Atlassian MCP searchJiraIssuesUsingJql tool to query:

JQL: project = ECD AND sprint in openSprints()

Return ONLY a JSON object with these fields:
{
  "total_issues": <count>,
  "sample_titles": [<first 3 issue titles>],
  "status_breakdown": {<status>: <count>, ...}
}

NO additional text, ONLY the JSON object.
"""

    print("📤 Sending prompt to Claude Code...")
    print(f"Prompt: {prompt[:100]}...\n")

    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text", "--settings", ".claude/settings.local.json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=60
        )

        print("📥 Claude Code Response:")
        print("=" * 60)
        print(result.stdout)
        print("=" * 60)

        if result.returncode != 0:
            print(f"\n❌ Error: {result.stderr}")
            return False

        # Try to parse JSON
        output = result.stdout.strip()

        # Extract JSON if wrapped in markdown
        if "```json" in output:
            json_start = output.find("```json") + 7
            json_end = output.find("```", json_start)
            json_str = output[json_start:json_end].strip()
        elif "```" in output:
            json_start = output.find("```") + 3
            json_end = output.find("```", json_start)
            json_str = output[json_start:json_end].strip()
        elif "{" in output and "}" in output:
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            json_str = output[json_start:json_end]
        else:
            print("\n❌ No JSON found in response")
            return False

        try:
            data = json.loads(json_str)
            print(f"\n✅ Successfully parsed JSON!")
            print(f"   Total Issues: {data.get('total_issues', 'N/A')}")
            print(f"   Sample Titles: {data.get('sample_titles', [])}")
            print(f"   Status Breakdown: {data.get('status_breakdown', {})}")
            return True
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parse error: {e}")
            print(f"   Attempted to parse: {json_str[:200]}...")
            return False

    except subprocess.TimeoutExpired:
        print("\n⏱️  Timeout after 60 seconds")
        return False
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_jira_query()
    sys.exit(0 if success else 1)
