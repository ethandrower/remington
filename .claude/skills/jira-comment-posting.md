# Jira Comment Posting with Mentions - Skill

## Purpose
This skill provides the correct way to post Jira comments with **clickable user mentions** that trigger notifications.

## Problem
The Atlassian MCP `addCommentToJiraIssue` tool does NOT properly support ADF (Atlassian Document Format) mentions. When you pass ADF JSON to it, the tool posts the raw JSON as literal text instead of rendering the mentions.

## Solution
Use the **REST API directly** via the helper script at `scripts/post_jira_comment.py`.

## How to Post a Jira Comment with Mentions

### Step 1: Gather Required Information
You need:
- **Issue Key**: e.g., "ECD-617"
- **Comment Text**: Your message with @Name placeholders
- **Account IDs**: For each user you want to mention (use `mcp__atlassian__lookupJiraAccountId()`)
- **Display Names**: For each user

### Step 2: Use the Helper Script

```bash
python scripts/post_jira_comment.py {issue_key} "Your comment with @Name" --mention-id "{accountId}" --mention-name "{Name}"
```

### Example: Single Mention

```bash
python scripts/post_jira_comment.py ECD-617 "Hi @Ethan, I've reviewed your ticket and posted my feedback." --mention-id "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e" --mention-name "Ethan"
```

**Result**: Jira comment will render as "Hi @Ethan Drower, I've reviewed your ticket and posted my feedback." with a clickable mention.

### Example: Multiple Mentions

```bash
python scripts/post_jira_comment.py ECD-456 "Hi @Mohamed and @Ahmed, please review this PR together." \
  --mention-id "712020:27a3f2fe-9037-455d-9392-fb80ba1705c0" --mention-name "Mohamed" \
  --mention-id "712020:another-account-id" --mention-name "Ahmed"
```

**Result**: Both Mohamed and Ahmed will receive Jira notifications with clickable mentions.

## Workflow for Responding to Jira Comments

When you need to respond to a Jira comment:

1. **Use MCP to gather context**:
   ```
   mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-617")
   mcp__atlassian__lookupJiraAccountId(searchString="Mohamed")
   ```

2. **Draft your response** with @Name placeholders

3. **Post using the script**:
   ```bash
   python scripts/post_jira_comment.py ECD-617 "Hi @Ethan, here's the status update..." \
     --mention-id "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e" --mention-name "Ethan"
   ```

4. **Report the action** in your summary:
   - "✅ Posted comment to ECD-617 with mention to @Ethan"
   - Include the exact comment text
   - Note the comment ID if available

## Technical Details

### ADF Mention Format
The script automatically constructs this ADF structure:

```json
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [
          {"type": "text", "text": "Hi "},
          {
            "type": "mention",
            "attrs": {
              "id": "712020:8a829eca-ce74-4a15-a5b9-9fc5d33c7c4e",
              "text": "@Ethan"
            }
          },
          {"type": "text", "text": ", here's the update..."}
        ]
      }
    ]
  }
}
```

### REST API Endpoint
The script posts to:
```
POST https://api.atlassian.com/ex/jira/{cloudId}/rest/api/3/issue/{issueKey}/comment
```

With headers:
- `Authorization: Bearer {ATLASSIAN_SERVICE_ACCOUNT_TOKEN}`
- `Content-Type: application/json`

## Important Notes

1. **Always use the script for comments with mentions** - Don't try to use the MCP tool
2. **MCP is fine for querying** - Use `getJiraIssue`, `lookupJiraAccountId`, etc.
3. **MCP is fine for field updates** - Use `editJiraIssue` for changing status, assignee, etc.
4. **The @Name in your text must match the --mention-name** - This is how the script knows where to insert the mention
5. **Account IDs are required** - Jira doesn't support mentions by username or email alone

## Common Mistakes to Avoid

❌ **DON'T**: Use `mcp__atlassian__addCommentToJiraIssue()` for mentions
❌ **DON'T**: Pass raw ADF JSON as a string
❌ **DON'T**: Use `[~accountid:...]` format (old Jira syntax, doesn't work in modern Jira)

✅ **DO**: Use `scripts/post_jira_comment.py`
✅ **DO**: Look up account IDs first with MCP
✅ **DO**: Include the @Name in your text matching the --mention-name

## Example Complete Workflow

```bash
# 1. Get issue context (use MCP)
mcp__atlassian__getJiraIssue(issueIdOrKey="ECD-617")

# 2. Look up user account ID (use MCP)
mcp__atlassian__lookupJiraAccountId(searchString="Mohamed Belkahla")
# Returns: 712020:27a3f2fe-9037-455d-9392-fb80ba1705c0

# 3. Post comment with mention (use script)
python scripts/post_jira_comment.py ECD-617 \
  "Hi @Mohamed, I've analyzed this ticket and found that it's blocked on ECD-500. Can you help prioritize?" \
  --mention-id "712020:27a3f2fe-9037-455d-9392-fb80ba1705c0" \
  --mention-name "Mohamed"

# 4. Verify success
# Script will output: ✅ Posted ADF comment to ECD-617 (comment ID: 12345)
```

## Related Files
- **Script**: `scripts/post_jira_comment.py`
- **Jira Monitor**: `bots/jira_monitor.py` (has `add_comment_with_adf()` method)
- **Documentation**: Official Atlassian ADF docs at developer.atlassian.com

## Troubleshooting

**Issue**: Script fails with "Missing Atlassian configuration"
**Fix**: Ensure `.env` has `ATLASSIAN_SERVICE_ACCOUNT_TOKEN` and `ATLASSIAN_CLOUD_ID`

**Issue**: Mention shows as plain text "@Name" instead of clickable
**Fix**: Verify the account ID is correct (use `lookupJiraAccountId` to confirm)

**Issue**: User didn't receive notification
**Fix**:
- Verify the account ID is correct
- Check that user has permission to view the ticket
- Jira doesn't notify users when they mention themselves
