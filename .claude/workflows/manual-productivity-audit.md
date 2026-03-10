# 🔍 Manual Developer Productivity Audit Workflow

## Overview

This workflow guides Claude through manually analyzing developer timesheet submissions against actual code complexity to identify potential productivity discrepancies.

## Audit Process

### Step 1: Extract Timesheet Data
1. Run the fixed timesheet analyzer to get recent ticket/hour data
2. Identify tickets with significant time investment (4+ hours)
3. Extract ticket numbers and associated developers

### Step 2: Ticket Requirements Analysis

#### Check Local Ticket References First
```bash
git log --grep="[TICKET-NUMBER]" --oneline --since="[TIMEFRAME]"
git branch -a | grep -i [TICKET-NUMBER]
```

#### Get Ticket Details from Jira MCP
```python
# Use Jira MCP to get official ticket description
ticket_details = get_jira_issue(ticket_number)
# Extract: summary, description, acceptance criteria, story points
```

#### Validate Ticket-to-Work Alignment
- **Does the branch name match the ticket?**
- **Do commit messages reference the ticket requirements?**
- **Does the code actually implement the described feature?**

### Step 3: For Each Flagged Ticket - Git Analysis

#### Find Related Branches
```bash
git branch -a | grep -i [TICKET-NUMBER]
```

#### Checkout and Analyze Branch
```bash
git checkout [BRANCH-NAME]
git log --oneline --since="[TIMEFRAME]" | head -10
```

#### View Recent Commits & Diffs
```bash
git log --stat --since="[TIMEFRAME]" | head -20
git diff HEAD~[N] HEAD --stat  # Compare recent changes
```

#### Cross-Reference with Ticket Requirements
- **Feature Match:** Does the code implement what the ticket describes?
- **Scope Alignment:** Is the work scope appropriate for claimed hours?
- **Quality Check:** Are acceptance criteria being addressed?

#### Assess Code Complexity
- **Lines of Code:** Count actual functional code changes
- **File Scope:** How many files were touched?
- **Logic Complexity:** New features vs simple changes?
- **Test Coverage:** Were tests added/modified?
- **Requirement Fulfillment:** Does code match ticket description?

### Step 4: Complexity Assessment Scale

#### 🟢 **Reasonable Hours-to-Code Ratio**
- **8+ hours:** Major feature (200+ LoC, multiple files, complex logic)
- **4-8 hours:** Medium feature (50-200 LoC, few files, moderate complexity)
- **1-4 hours:** Small changes (1-50 LoC, simple fixes, config changes)

#### 🟡 **Investigate Further**
- High hours but minimal code changes
- Code changes don't match described work
- Only documentation/comment updates

#### 🔴 **Red Flags**
- 8+ hours billed, <25 LoC changed
- No commits found for claimed work hours
- Ticket marked complete but branch not merged

### Step 5: Generate Assessment Report

For each analyzed ticket, document:
- **Developer & Ticket**
- **Hours Billed**
- **Code Analysis:** LoC, files changed, complexity type
- **Assessment:** Reasonable/Investigate/Red Flag
- **Reasoning:** Why this ratio makes sense or doesn't

## Example Manual Audit

### Ticket: ECD-125 (Valentin S, 7h billed)

```bash
git branch -a | grep -i ecd-125
# Found: remotes/origin/ECD-125-citation-api-fixes

git checkout ECD-125-citation-api-fixes
git log --oneline --since="1 week ago"
# Shows 3 commits over 2 days

git log --stat --since="1 week ago" | head -15
# Results:
# - Modified 4 files
# - Added 45 lines, removed 12 lines
# - Changes in api/citation.py, tests/test_citation.py
# - Bug fixes + new error handling + tests
```

**Assessment:** ✅ **Reasonable**
- **7h for 57 LoC across 4 files with tests = Good ratio**
- **API integration work typically complex**
- **Added error handling and test coverage**

### Ticket: ECD-298 (User_K1K2, 8h billed)

```bash
git branch -a | grep -i ecd-298
# No branches found

git log --grep="ECD-298" --since="2 weeks ago" --oneline
# No commits found
```

**Assessment:** 🔴 **Red Flag**
- **8h billed but NO code evidence found**
- **Investigate immediately - what was actually done?**

## Workflow Integration

### When to Run Manual Audit
- Weekly after timesheet submissions
- When developers report >6h on single tickets
- For tickets marked "complete" but status unclear

### Reporting Format
Create summary with:
- **🔴 Red Flags:** Immediate investigation needed
- **🟡 Investigate:** Require clarification from developer
- **✅ Reasonable:** Good hours-to-code ratio
- **🌟 Excellent:** Exceptional productivity

### Follow-up Actions
- **Red Flags:** Direct developer conversation
- **Investigate:** Request additional context in Slack/Jira
- **Excellent:** Recognize publicly for great work

---
*This manual process ensures human judgment in assessing code complexity vs billed hours*
