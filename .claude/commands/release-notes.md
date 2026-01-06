# Release Notes Generator

Generate customer-facing release notes in Confluence from completed Jira issues.

## Workflow

### Step 1: Determine Version
Find the current release version from fix versions in recent completed issues.

```bash
python -m src.tools.jira.get_release_issues --days 14 | head -50
```

Look at the `fix_versions` field to determine the current version. If none, default to the next minor version.

### Step 2: Find or Create Release Notes Page

Search for existing release notes page:
```bash
python -m src.tools.confluence.search "title ~ 'Customer Release Notes' AND title ~ 'VERSION' AND space = ECD"
```

If no page exists, create one:
```bash
python -m src.tools.confluence.create_page "Customer Release Notes – Evidence Cloud vVERSION" \
  --space-key ECD \
  --parent-id 125566979 \
  --body "INITIAL_CONTENT"
```

Parent page ID 125566979 is the "Customer Release Notes" container in ECD space.

### Step 3: Get Completed Issues
```bash
python -m src.tools.jira.get_release_issues --days 30
```

### Step 4: Check Which Issues Are Missing

For each completed issue, check if its Jira key (e.g., "ECD-123") appears in the release notes page content.

```bash
python -m src.tools.confluence.get_page PAGE_ID
```

### Step 5: Generate Marketing-Style Writeups

For each issue NOT already in the release notes, generate a customer-facing writeup:

**Format:**
- **Heading**: Feature/fix title
- **Reference**: Link to Jira ticket
- **Value Proposition**: 1-2 sentences explaining WHY this is useful
- **Details** (optional): Brief technical context if relevant

**Tone:**
- Customer-focused (benefits, not implementation)
- Professional but approachable
- Actionable (how does this help them?)

**Example Writeups by Type:**

**Story/Feature:**
> ### Enhanced PDF Export with Attachments
> Your export workflow just got more powerful. You can now include all related attachments when exporting to PDF, keeping your evidence complete and presentation-ready in a single file.

**Bug Fix:**
> ### Fixed: Company Creation Wizard
> We've resolved an issue that prevented new companies from being created through the setup wizard. The onboarding experience is now smooth and reliable.

**Performance:**
> ### Faster AI Extraction
> Your AI-powered extractions now complete up to 40% faster, helping you move through large document sets more efficiently.

### Step 6: Update Release Notes Page

Use the update_page tool or add_feature_to_release_notes to add new entries.

### Step 7: Report Summary

After completing, report:
- Version processed
- Issues checked
- New entries added
- Any issues skipped (already present)

## Configuration

- **Parent Page ID**: `125566979` (Customer Release Notes)
- **Space Key**: `ECD` (Evidence Cloud Documentation)
- **Engineering Space**: `Engineerin` (for internal drafts)

## Tools Available

- `python -m src.tools.jira.get_release_issues` - Get completed issues
- `python -m src.tools.confluence.search` - Find pages
- `python -m src.tools.confluence.get_page` - Read page content
- `python -m src.tools.confluence.create_page` - Create new page
- `python -m src.tools.confluence.update_page` - Update page

## Arguments

- `$VERSION` - Optional version override (e.g., "5.5.6")
- `$DAYS` - Look back period for completed issues (default: 30)
