# Atlassian CLI Utility

**Purpose:** Standalone command-line tools for Jira and Confluence API operations, serving as a backup when Atlassian MCP is unavailable.

## Tools Included

1. **jira-cli** - Jira issue management
2. **confluence-cli** - Confluence page management

## Installation

No installation required! These are standalone Python scripts that use the same credentials from your `.env` file.

### Dependencies

Ensure you have these Python packages installed:

```bash
pip install requests python-dotenv
```

## Configuration

The CLI tools read credentials from `/Users/ethand320/code/citemed/project-manager/.env`:

```bash
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=your-email@atlassian.com
ATLASSIAN_SERVICE_ACCOUNT_TOKEN=your_api_token_here
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
```

## Jira CLI Usage

### Get Issue Details

```bash
./jira-cli issue get ECD-539
./jira-cli issue get ECD-539 --json  # Full JSON output
```

### Create Issues

```bash
# Create a story
./jira-cli issue create --project ECD --type Story --summary "Implement new feature"

# Create with description
./jira-cli issue create --project ECD --type Task \
  --summary "Fix authentication bug" \
  --description "Users are unable to log in when using SSO"
```

### Create Subtasks

```bash
./jira-cli subtask create --parent ECD-539 --summary "Configure Airflow DAG"

./jira-cli subtask create --parent ECD-539 \
  --summary "Implement error handling" \
  --description "Add retry logic with exponential backoff"
```

### Update Issues

```bash
# Assign to someone
./jira-cli issue update ECD-123 --assignee mohamed@citemed.com

# Update summary
./jira-cli issue update ECD-123 --summary "New summary text"

# Update description
./jira-cli issue update ECD-123 --description "Updated description"
```

### Add Comments

```bash
# Simple comment
./jira-cli comment add ECD-123 "This looks good, approved!"

# Comment with mentions
./jira-cli comment add ECD-123 "Please review this @Mohamed" \
  --mention mohamed@citemed.com
```

### Search Issues (JQL)

```bash
# Basic search
./jira-cli search "project = ECD AND status = 'In Progress'"

# Verbose output
./jira-cli search "assignee = currentUser()" --verbose

# Limit results
./jira-cli search "project = ECD" --max-results 10
```

### Transition Issues

```bash
# Move to Done
./jira-cli transition ECD-123 "Done"

# Move to In Progress
./jira-cli transition ECD-123 "In Progress"
```

### Search Users

```bash
# Find user by email
./jira-cli user search mohamed@citemed.com

# Find by name
./jira-cli user search Mohamed
```

## Confluence CLI Usage

### Get Page Details

```bash
./confluence-cli page get 123456
./confluence-cli page get 123456 --json  # Full JSON output
```

### Create Pages

```bash
# Create page in space
./confluence-cli page create --space ECD \
  --title "Implementation Plan" \
  --content "<p>This is the content</p>"

# Create child page
./confluence-cli page create --space ECD \
  --title "Sub-page" \
  --content "<p>Content here</p>" \
  --parent 123456
```

### Update Pages

```bash
# Update content only
./confluence-cli page update 123456 --content "<p>New content</p>"

# Update title and content
./confluence-cli page update 123456 \
  --title "Updated Title" \
  --content "<p>New content</p>"
```

### Search Confluence

```bash
# Search by text
./confluence-cli search "type=page AND text~'implementation'"

# Search in space
./confluence-cli search "space=ECD AND title~'sprint'"

# Limit results
./confluence-cli search "type=page" --limit 10
```

### List Spaces

```bash
./confluence-cli space list
./confluence-cli space list --limit 50
```

## Common Use Cases

### Bulk Create Subtasks from Files

```bash
# Create all subtasks for ECD-539
for file in ../../ethan_local/ecd-539-stories/WEEK*.md; do
  summary=$(grep "^# " "$file" | sed 's/# ECD-539-[0-9]*: //')
  description=$(sed -n '/## Description/,/^##/p' "$file" | grep -v "^##")

  ./jira-cli subtask create --parent ECD-539 \
    --summary "$summary" \
    --description "$description"
done
```

### Monitor Sprint Progress

```bash
# Get all in-progress tickets
./jira-cli search "project = ECD AND sprint in openSprints() AND status = 'In Progress'" -v

# Find blocked tickets
./jira-cli search "project = ECD AND status = Blocked"
```

### Automate Daily Standup

```bash
# Get your tickets updated today
./jira-cli search "assignee = currentUser() AND updated >= -1d" -v
```

### Find Stale PRs

```bash
# Tickets in Pending Approval for >2 days
./jira-cli search "project = ECD AND status = 'Pending Approval' AND updated <= -2d"
```

## Integration with PM Agent

The PM agent can use these CLI tools when MCP is unavailable:

```python
# In agents/jira-manager.py or workflows
import subprocess

def create_subtask_via_cli(parent_key, summary, description):
    """Fallback to CLI when MCP is down."""
    cmd = [
        "scripts/atlassian-cli/jira-cli",
        "subtask", "create",
        "--parent", parent_key,
        "--summary", summary,
        "--description", description
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        return result.stdout
    else:
        raise Exception(f"CLI failed: {result.stderr}")
```

## Error Handling

Both CLIs provide detailed error messages:

- **401 Unauthorized:** Check your API token in `.env`
- **404 Not Found:** Issue/page doesn't exist or you lack permissions
- **400 Bad Request:** Invalid input (check required fields)

All errors include the full API response for debugging.

## Advanced Features

### Custom JQL Queries

```bash
# Complex sprint analysis
./jira-cli search "project = ECD AND sprint = 'Sprint 42' AND (status changed to 'Done' during (startOfDay(-7d), now()))"

# Developer productivity
./jira-cli search "assignee = mohamed@citemed.com AND resolved >= -7d"
```

### Batch Operations

```bash
# Transition multiple tickets
for issue in ECD-101 ECD-102 ECD-103; do
  ./jira-cli transition "$issue" "Done"
done
```

### Export to JSON

```bash
# Export sprint data
./jira-cli search "project = ECD AND sprint in openSprints()" --json > sprint_data.json
```

## Troubleshooting

### "Module not found" errors

```bash
cd /Users/ethand320/code/citemed/project-manager
pip install -r requirements.txt
```

### "Permission denied"

```bash
chmod +x scripts/atlassian-cli/jira-cli
chmod +x scripts/atlassian-cli/confluence-cli
```

### "Missing credentials"

Ensure `.env` has all required fields:

```bash
cat .env | grep ATLASSIAN
```

## Extending the CLI

To add new commands:

1. Add a new subparser in `main()`
2. Create a `cmd_*` handler function
3. Add the API method to `JiraClient` or `ConfluenceClient`

Example:

```python
# Add to JiraClient
def assign_to_me(self, issue_key: str):
    """Assign issue to current user."""
    response = self._request("GET", "myself")
    me = response.json()

    self.update_issue(issue_key, assignee={'accountId': me['accountId']})

# Add command handler
def cmd_assign_me(client, args):
    client.assign_to_me(args.issue_key)
    print(f"✓ Assigned {args.issue_key} to you")

# Add to argparse
assign_me = subparsers.add_parser('assign-me', help='Assign issue to yourself')
assign_me.add_argument('issue_key')
```

## Comparison with MCP

| Feature | Atlassian MCP | This CLI |
|---------|---------------|----------|
| **Availability** | Requires MCP server running | Always available |
| **Speed** | Slower (protocol overhead) | Faster (direct API) |
| **Error Handling** | Limited visibility | Detailed HTTP responses |
| **Scriptability** | Difficult to script | Easy shell integration |
| **Use Case** | Interactive Claude sessions | Automation, fallback |

**Recommendation:** Use MCP when available for Claude integration, fall back to CLI for automation and when MCP is down.

---

**Maintained by:** CiteMed PM Agent
**Last Updated:** 2025-10-21
**Version:** 1.0.0
