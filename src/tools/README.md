# Direct API Tools

This module provides direct REST API tools that mirror the MCP Atlassian functions. These tools are used by Claude Code subprocess calls and will later become LangChain tools for the Deep Agents migration.

## Why Direct API Instead of MCP?

1. **Reliability** - MCP OAuth tokens expire and require interactive re-auth
2. **Service Account** - Uses API tokens that never expire
3. **Subprocess Compatible** - Works when Claude Code runs as a subprocess
4. **Migration Path** - Same tools become LangChain tools for Deep Agents

## Tool Mapping: MCP → Direct API

### Priority 1: Core Jira Tools (Essential for PM Agent)

| MCP Function | Our Tool | Status | Description |
|--------------|----------|--------|-------------|
| `mcp__atlassian__searchJiraIssuesUsingJql` | `jira/search.py` | ✅ DONE | Search issues with JQL |
| `mcp__atlassian__getJiraIssue` | `jira/get_issue.py` | ✅ DONE | Get full issue details |
| `mcp__atlassian__addCommentToJiraIssue` | `jira/add_comment.py` | ✅ DONE | Post comment with @mentions |
| `mcp__atlassian__editJiraIssue` | `jira/edit_issue.py` | ✅ DONE | Update issue fields |
| `mcp__atlassian__transitionJiraIssue` | `jira/transition_issue.py` | ✅ DONE | Change issue status |
| `mcp__atlassian__getTransitionsForJiraIssue` | `jira/get_transitions.py` | ✅ DONE | Get available transitions |
| `mcp__atlassian__lookupJiraAccountId` | `jira/lookup_user.py` | ✅ DONE | Find user account IDs |
| `mcp__atlassian__getVisibleJiraProjects` | `jira/list_projects.py` | ✅ DONE | List accessible projects |

### Priority 2: Sprint & Agile Tools

| MCP Function | Our Tool | Status | Description |
|--------------|----------|--------|-------------|
| N/A (Agile API) | `jira/get_sprint.py` | 🔨 TODO | Get sprint details |
| N/A (Agile API) | `jira/get_sprint_issues.py` | 🔨 TODO | Get issues in sprint |
| N/A (Agile API) | `jira/get_board.py` | 🔨 TODO | Get board configuration |

### Priority 3: Confluence Tools

| MCP Function | Our Tool | Status | Description |
|--------------|----------|--------|-------------|
| `mcp__atlassian__getConfluencePage` | `confluence/get_page.py` | 🔨 TODO | Read page content |
| `mcp__atlassian__searchConfluenceUsingCql` | `confluence/search.py` | 🔨 TODO | Search with CQL |
| `mcp__atlassian__createConfluencePage` | `confluence/create_page.py` | 🔨 TODO | Create new page |
| `mcp__atlassian__updateConfluencePage` | `confluence/update_page.py` | 🔨 TODO | Update existing page |

### Priority 4: Bitbucket Tools

| MCP Function | Our Tool | Status | Description |
|--------------|----------|--------|-------------|
| N/A (Bitbucket API) | `bitbucket/list_prs.py` | 🔨 TODO | List open PRs |
| N/A (Bitbucket API) | `bitbucket/get_pr.py` | 🔨 TODO | Get PR details |
| N/A (Bitbucket API) | `bitbucket/get_pr_diff.py` | 🔨 TODO | Get PR diff |
| N/A (Bitbucket API) | `bitbucket/add_pr_comment.py` | 🔨 TODO | Post PR comment |
| N/A (Bitbucket API) | `bitbucket/get_commits.py` | 🔨 TODO | Get commit history |

## Usage

Each tool is a standalone Python script that can be called from CLI:

```bash
# Search Jira
python -m src.tools.jira.search "project = ECD AND status = 'In Progress'" --max-results 10

# Get issue details
python -m src.tools.jira.get_issue ECD-123

# Add comment with mentions
python -m src.tools.jira.add_comment ECD-123 "Hi @Ethan, reviewed!" --mention "712020:xxx" "Ethan"

# Transition issue
python -m src.tools.jira.transition_issue ECD-123 "In Progress"

# Lookup user
python -m src.tools.jira.lookup_user "ethan@citemed.com"
```

## Authentication

All tools use service account authentication via environment variables:

```bash
# Required in .env
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=remington-cd3wmzelbd@serviceaccount.atlassian.com
ATLASSIAN_SERVICE_ACCOUNT_TOKEN=your_api_token_here
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
```

## Directory Structure

```
src/tools/
├── README.md                 # This file
├── __init__.py
├── base.py                   # Shared auth and utilities
├── jira/
│   ├── __init__.py
│   ├── search.py             # searchJiraIssuesUsingJql
│   ├── get_issue.py          # getJiraIssue
│   ├── add_comment.py        # addCommentToJiraIssue
│   ├── edit_issue.py         # editJiraIssue
│   ├── transition_issue.py   # transitionJiraIssue
│   ├── get_transitions.py    # getTransitionsForJiraIssue
│   ├── lookup_user.py        # lookupJiraAccountId
│   ├── list_projects.py      # getVisibleJiraProjects
│   ├── get_sprint.py         # Agile API
│   └── get_sprint_issues.py  # Agile API
├── confluence/
│   ├── __init__.py
│   ├── get_page.py
│   ├── search.py
│   ├── create_page.py
│   └── update_page.py
└── bitbucket/
    ├── __init__.py
    ├── list_prs.py
    ├── get_pr.py
    ├── get_pr_diff.py
    ├── add_pr_comment.py
    └── get_commits.py
```

## Future: LangChain Tools

These same functions will become LangChain tools for the Deep Agents migration:

```python
from langchain_core.tools import tool
from src.tools.jira.search import search_jira

@tool
def jira_search(jql: str, max_results: int = 50) -> dict:
    """Search Jira issues using JQL query."""
    return search_jira(jql, max_results)
```