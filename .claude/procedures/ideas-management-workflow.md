# Ideas Management Workflow - CiteMed Jira

## Overview

CiteMed uses **Jira Product Discovery** for idea management with a dedicated Ideas project (MDP) that feeds into implementation projects (ECD, AI).

## Project Structure

### Ideas Projects
- **MDP** ("Ideas Discovery - CiteMed") - Primary ideas project
  - Project Type: `product_discovery`
  - Issue Type: `Idea` only
  - Key: MDP-XXX

- **CI** ("Customer Insights") - Customer-specific ideas
  - Project Type: `product_discovery`
  - Issue Type: `Idea` only
  - Key: CI-XXX

### Implementation Projects
- **ECD** ("Evidence Cloud Development") - Main product development
  - Issue Types: Story, Task, Bug, Epic, Initiative
  - Key: ECD-XXX

- **AI** ("AI Module") - AI-specific features
  - Issue Types: Story, Task, Bug, Epic, Initiative
  - Key: AI-XXX

## Workflow: Creating a New Product Idea

### Step 1: Create Idea in MDP Project

Use the Atlassian MCP tool to create ideas:

```typescript
mcp__atlassian__createJiraIssue({
  cloudId: "67bbfd03-b309-414f-9640-908213f80628",
  projectKey: "MDP",  // Ideas project
  issueTypeName: "Idea",
  summary: "Feature title (brief)",
  description: `
## Problem Statement
What user problem does this solve?

## Proposed Solution
Brief description of the approach

## User Benefits
- Benefit 1
- Benefit 2

## Design Considerations
Key technical or UX considerations

## Related Work
Links to related ECD/AI tickets

## Context
**Source**: Customer request / Internal / Competitive
**Priority**: High / Medium / Low
**Motivation**: Why now?
  `,
  additional_fields: {
    labels: ["ux", "category-tag", "source-tag"]
  }
})
```

### Step 2: Search for Duplicates (Optional but Recommended)

Before creating, search for similar ideas:

```typescript
// Search in MDP for existing ideas
mcp__atlassian__searchJiraIssuesUsingJql({
  cloudId: "67bbfd03-b309-414f-9640-908213f80628",
  jql: "project = MDP AND issuetype = Idea AND status != Done",
  fields: ["key", "summary", "description", "status"]
})

// Use Atlassian Rovo Search for semantic matching
mcp__atlassian__search({
  query: "extraction fields configuration UX"
})
```

### Step 3: Link to Related Implementation Work

When an idea relates to existing or planned implementation work, create issue links.

**Link Types:**
- `implements` (outward) / `is implemented by` (inward) - MDP idea → ECD/AI story
- `relates to` - General relationship

**Example:** MDP-95 (Idea) → AI-81 (Story implementing it)

**Method 1: Direct API Linking (Preferred)**

Use the Jira REST API via Bash tool to create actual issue links:

```bash
# Get credentials from environment
ATLASSIAN_CLOUD_ID="67bbfd03-b309-414f-9640-908213f80628"

# Create issue link using Jira API
curl -X POST \
  "https://api.atlassian.com/ex/jira/$ATLASSIAN_CLOUD_ID/rest/api/3/issueLink" \
  -u "$ATLASSIAN_API_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": {
      "name": "Implements"
    },
    "inwardIssue": {
      "key": "MDP-96"
    },
    "outwardIssue": {
      "key": "ECD-808"
    },
    "comment": {
      "body": "Linked idea to implementation story via /idea workflow"
    }
  }'
```

**Available Link Types:**
- `"Implements"` - For MDP idea → ECD/AI implementation
- `"Relates"` - For general relationships
- `"Blocks"` - For dependencies

**Method 2: Fallback with Comments**

If API linking fails, add comments on both tickets:

```typescript
mcp__atlassian__addCommentToJiraIssue({
  cloudId: "67bbfd03-b309-414f-9640-908213f80628",
  issueIdOrKey: "MDP-96",
  commentBody: `
## Related Implementation Work

This idea is implemented by:
- [ECD-808](https://citemed.atlassian.net/browse/ECD-808): Automatically generate field names
- [ECD-809](https://citemed.atlassian.net/browse/ECD-809): Show extraction field description as tooltip
- [ECD-811](https://citemed.atlassian.net/browse/ECD-811): Handle long extractions in text fields

**Epic:** [ECD-71](https://citemed.atlassian.net/browse/ECD-71) (Extraction Field Templates)
  `
})
```

## Workflow: Converting Idea to Implementation

### When an Idea is Approved

1. **Create Epic/Story in ECD or AI**
   - Create Epic (for large features) or Story (for small features)
   - Reference the MDP idea in the description

2. **Link Idea to Implementation**
   - Manually link in Jira UI: MDP-XX "is implemented by" ECD-XXX
   - Or add comment on both tickets referencing each other

3. **Update Idea Status**
   - Move MDP idea through workflow: Discovery → Validated → In Progress → Shipped

### Example: Full Workflow

```markdown
1. User requests feature → Create MDP-96 (Idea)
2. Product review & prioritization
3. Approved → Create ECD-846 (Story or Epic)
4. Link: MDP-96 "is implemented by" ECD-846
5. Implementation: ECD-846 moves through development workflow
6. When shipped: Mark MDP-96 as "Shipped"
```

## /idea Slash Command Workflow

The `/idea` command should execute this 9-step process:

1. **Gather Idea Description** - Prompt user for details
2. **Search for Duplicates** - Check MDP + Rovo search
3. **Present Similar Ideas** - Show matches, ask to proceed or merge
4. **User Confirms New** - Get confirmation
5. **Search Related Stories** - Find ECD/AI tickets that relate
6. **AI-Powered Link Suggestions** - Analyze relationships
7. **User Approves Links** - Confirm which to reference
8. **Create Idea in MDP** - Create MDP-XXX ticket
9. **Add Comment with Links** - Document related implementation work
10. **Notify User** - Show MDP-XXX link

## Best Practices

### Idea Creation
- ✅ **Always create Ideas in MDP**, not ECD/AI
- ✅ Use descriptive summaries (5-10 words)
- ✅ Include problem statement and user benefits
- ✅ Tag with relevant labels (ux, api, extraction, reports, etc.)
- ✅ Set context: source, priority, motivation

### Linking Ideas to Implementation
- ✅ Search for related ECD/AI work before creating
- ✅ Document relationships via comments when direct linking unavailable
- ✅ One idea can relate to multiple implementation tickets
- ✅ One epic can implement multiple ideas

### Avoid
- ❌ Creating "Idea" tickets in ECD or AI projects (they don't have Idea type)
- ❌ Creating Stories in MDP (it only supports Ideas)
- ❌ Skipping duplicate search (creates clutter)
- ❌ Leaving ideas unlinked to implementation work

## Issue Link Types Reference

| Link Type | Outward | Inward | Use Case |
|-----------|---------|--------|----------|
| Implements | implements | is implemented by | Idea → Story/Epic |
| Relates | relates to | relates to | General connection |
| Blocks | blocks | is blocked by | Dependency |

## Configuration

**CloudId:** `67bbfd03-b309-414f-9640-908213f80628`

**Projects:**
- MDP (Ideas): `projectKey: "MDP"`, `issueTypeName: "Idea"`
- ECD (Implementation): `projectKey: "ECD"`, `issueTypeName: "Story" | "Epic"`
- AI (Implementation): `projectKey: "AI"`, `issueTypeName: "Story" | "Epic"`

## Examples

### Example 1: Simple Idea → Story

**Step 1:** Create idea
```
MDP-96: Redesign Extraction Fields Configuration Page
Status: Discovery
```

**Step 2:** Approved, create story
```
ECD-846: Implement expandable table for extraction fields config
Parent: ECD-643 (Adhoc UX Updates epic)
```

**Step 3:** Link
```
MDP-96 "is implemented by" ECD-846
```

### Example 2: Complex Idea → Epic + Multiple Stories

**Step 1:** Create idea
```
MDP-94: Extraction Only Project Type
Status: Discovery
```

**Step 2:** Approved, create epic
```
ECD-730: Extraction Only Project Type (Epic)
Stories:
- ECD-731: Project wizard UI updates
- ECD-732: Generate reports without protocol validation
- ECD-733: PDF upload workflow
```

**Step 3:** Link
```
MDP-94 "is implemented by" ECD-730 (Epic)
```

## Future Improvements

### Needed Capabilities
1. ✅ **Direct Issue Linking API** - Implemented via curl to Jira REST API
2. **Automated Duplicate Detection** - AI-powered semantic search
3. **Status Sync** - Auto-update MDP idea status when implementation ships
4. **Impact Scoring** - Track which ideas drive most user value

### Current Capabilities
- ✅ Direct API linking via Bash/curl to Jira REST API
- ✅ Fallback to comments when API linking fails
- ✅ MCP-based idea creation in MDP project
- ✅ Duplicate search using JQL and Rovo search

---

**Last Updated:** 2025-11-24
**Maintained By:** Project Manager Agent
