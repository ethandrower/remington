# /idea - Intelligent Idea Ingestion Workflow

You are executing the **Intelligent Idea Ingestion Workflow** for creating new product ideas in Jira with automatic deduplication and story linking.

## Workflow Overview

This command implements the workflow described in FUTURE_WORK.md section 0: Intelligent Idea Ingestion Workflow.

## Your Task - Execute All 9 Steps

### Step 1: Gather Idea Description
- Prompt user for the idea description if not provided
- Ask for context: customer request, internal brainstorm, competitive feature, etc.
- Get priority signal if available (P0/P1/P2/P3 or High/Medium/Low)

### Step 2: Search for Duplicate Ideas
- Use Jira search to find similar existing ideas:
  ```
  Tool: mcp__atlassian__searchJiraIssuesUsingJql
  JQL: project = MDP AND issuetype = Idea AND status != Done
  ```
- Extract keywords from user's idea description
- Use Atlassian search tool to find text matches:
  ```
  Tool: mcp__atlassian__search
  Query: <extracted keywords>
  ```
- Score similarity (simple keyword overlap for now, or ask Claude to assess)
- Threshold: >70% similarity = potential duplicate

### Step 3: Present Similar Ideas (if found)
- Show user list of similar ideas with:
  - Jira ticket key and title
  - Brief description
  - Current status
  - Similarity reasoning
- Ask: "Is your idea different from these? Reply 'yes' to proceed or 'merge with MDP-XXX' to link instead"
- If user wants to merge, link to existing idea and exit workflow

### Step 4: User Confirms Idea is New
- Wait for user confirmation to proceed
- If user provides refinements, incorporate them

### Step 5: Search for Related Stories
- Use JQL to find potentially related stories:
  ```
  JQL: project = ECD AND issuetype IN (Story, Task, Bug) AND status != Done
  ```
- Filter to stories with keyword matches
- Look for stories in same epic or with similar labels
- Limit to top 10-15 most relevant

### Step 6: AI-Powered Link Suggestions
- For each related story, use Claude to evaluate:
  - Is this story related to the new idea?
  - How is it related? (implements, blocks, relates to)
  - Confidence level (high/medium/low)
- Present to user:
  ```
  I found these stories that may be related:

  1. ✅ ECD-543: User authentication system
     Relation: Implements | Confidence: High
     Reason: Idea requires auth, this story provides it

  2. ⚠️ ECD-555: Dashboard redesign
     Relation: Relates to | Confidence: Medium
     Reason: Both touch user profile UI
  ```

### Step 7: User Approves Links
- Present list of suggested story links
- Ask user to confirm which ones to link
- Allow user to add/remove from list
- For each link, ask for relationship type:
  - "relates to" (default)
  - "blocks" (this idea can't proceed without that story)
  - "is blocked by" (that story needs this idea)
  - "implements" (that story will implement this idea)

### Step 8: Create Jira Idea + Links
- Create the Jira Idea ticket in MDP project:
  ```
  Tool: mcp__atlassian__createJiraIssue
  Parameters:
    - cloudId: 67bbfd03-b309-414f-9640-908213f80628
    - projectKey: MDP
    - issueTypeName: Idea
    - summary: <user's idea title>
    - description: <formatted description>
  ```
- **Create Issue Links via Jira API** (MCP doesn't support direct linking):
  ```bash
  # Get Atlassian credentials from environment
  ATLASSIAN_CLOUD_ID="67bbfd03-b309-414f-9640-908213f80628"
  ATLASSIAN_API_EMAIL="<from env>"
  ATLASSIAN_API_TOKEN="<from env>"

  # Create issue link (MDP idea -> ECD story)
  curl -X POST \
    "https://api.atlassian.com/ex/jira/$ATLASSIAN_CLOUD_ID/rest/api/3/issueLink" \
    -H "Authorization: Basic $(echo -n $ATLASSIAN_API_EMAIL:$ATLASSIAN_API_TOKEN | base64)" \
    -H "Content-Type: application/json" \
    -d '{
      "type": {
        "name": "Implements"
      },
      "inwardIssue": {
        "key": "MDP-99"
      },
      "outwardIssue": {
        "key": "ECD-177"
      },
      "comment": {
        "body": "Linked idea to implementation story"
      }
    }'
  ```
- **Fallback**: Add comments on both tickets cross-referencing each other
- Store metadata about creation (date, workflow used, links created)

### Step 9: Notify Stakeholders
- Post to Slack (if SLACK_IDEAS_CHANNEL_ID configured):
  ```
  🆕 New Idea Created: MDP-XXX

  <Idea summary>

  Source: <customer/internal/competitive>
  Priority: <if set>

  Related Stories: 3 linked
  - ECD-543: User authentication
  - ECD-555: Dashboard redesign
  - ECD-601: API improvements

  🔗 View in Jira: https://citemed.atlassian.net/browse/MDP-XXX
  ```

### Step 10: Confirmation
- Show user the created idea key
- List all linked stories
- Provide Jira link

## Configuration

**Required:**
- Atlassian MCP connection configured
- CloudId: `67bbfd03-b309-414f-9640-908213f80628`
- Project: MDP (Ideas Discovery - CiteMed)

**Optional:**
- `SLACK_IDEAS_CHANNEL_ID` in .env for Slack notifications
- Priority levels configured in Jira

## Example Usage

```
User: /idea add bulk evidence import via CSV
Assistant:
  Let me help you create this idea. First, let me search for similar existing ideas...

  I found 1 potentially similar idea:
  - MDP-85: Batch document upload

  Is your idea different from this? [proceeds with workflow]
```

## Handling Edge Cases

1. **No similar ideas found:** Skip to Step 5 (search related stories)
2. **User wants to merge:** Link description/comment to existing idea, exit workflow
3. **No related stories found:** Create idea without links, notify user
4. **User cancels mid-workflow:** Confirm cancellation, don't create idea
5. **Jira creation fails:** Show error, save description for retry

## Important Notes

- This is for **company product ideas** in Jira, not PM agent improvements
- For PM agent improvements, use `/future` instead
- Always search for duplicates first to prevent clutter
- Be thorough in link suggestions - this is the key value-add
- Store workflow metadata for analytics
- If Slack channel not configured, skip notification step

## Success Criteria

- Idea created in Jira with proper formatting
- Duplicates detected and prevented (or merged)
- Relevant stories linked automatically
- User feels confident idea won't get lost
- Stakeholders notified via Slack (if configured)
