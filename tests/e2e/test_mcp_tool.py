"""
Quick test to see what the Atlassian MCP addCommentToJiraIssue tool actually expects
"""
import json

# Try to query the MCP server for tool schemas
print("Testing MCP tool parameter investigation...")

# The tool should be accessible via Claude Code
# Let's see if we can get its schema

print("\nAttempting to use mcp__atlassian__addCommentToJiraIssue with plain text...")
print("Expected parameters:")
print("  - issueIdOrKey: string")
print("  - body: string (likely plain text, NOT JSON)")
print("\nHypothesis: The tool accepts plain text and converts to ADF internally")
print("For mentions, it might:")
print("  1. Auto-detect @username patterns")
print("  2. Accept special syntax like @{accountId}")
print("  3. Have a separate 'mentions' parameter")
print("  4. Not support mentions at all")

