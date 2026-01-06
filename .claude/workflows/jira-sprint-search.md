# Jira Sprint Search Workflow

## PM Subagent: Current Sprint Analysis

### Overview
This workflow documents the process for searching and analyzing current sprint items in Jira using the Atlassian MCP connection.

### Prerequisites
- Atlassian MCP connection configured and authenticated
- Access to the ECD project in Jira
- Valid cloudId for the Atlassian instance

### Step 1: Test MCP Connection
```
Tool: mcp__atlassian__getAccessibleAtlassianResources
Purpose: Verify connection and retrieve available cloudIds
```

### Step 2: Search Current Sprint
```
Tool: mcp__atlassian__searchJiraIssuesUsingJql
Parameters:
  - cloudId: [obtained from step 1]
  - jql: "project = ECD AND sprint in openSprints()"
  - fields: ["summary", "description", "status", "issuetype", "priority", "created"]
  - maxResults: 100
```

### Step 3: Analyze Sprint Composition
Parse the results to categorize:
- **Issue Types**: Stories, Tasks, Bugs, Epics
- **Modules**: Identify which product modules are being worked on
- **Priority Distribution**: High, Medium, Low priority items
- **Status Distribution**: To Do, In Progress, Done

### Step 4: Generate Sprint Summary
Create a structured summary including:
- Total issue count
- Module breakdown (e.g., CiteSource Module, Word Add-in, etc.)
- Key features being developed
- Sprint focus areas

### Example Output Format
```
Current Sprint Summary:
- Total Items: 25
- Primary Module: CiteSource Module (16 items)
- Key Features:
  * Word Add-in functionality (ECD-409, ECD-410)
  * Citation management (ECD-327, ECD-329, ECD-330, ECD-331, ECD-332)
  * Full-text article requests (ECD-397, ECD-398)
- Sprint Focus: Core citation workflow improvements
```

### Troubleshooting
- **404/503 Errors**: User may need to reconnect Atlassian integration
- **Empty Results**: Verify JQL syntax and project access
- **Wrong Results**: Ensure using `sprint in openSprints()` not specific sprint names

### Follow-up Actions
This workflow can be extended to:
- Compare sprint velocity across iterations
- Identify blocked items
- Generate detailed module reports
- Track epic progress across sprints
