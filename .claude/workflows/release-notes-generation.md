# Release Notes Generation Workflow

**Purpose:** Automated workflow for writing comprehensive release notes from Jira tickets in Confluence.

**Agent:** Jira Manager + Sprint Analyzer
**Frequency:** On-demand (before each release)
**Duration:** ~15-30 minutes

---

## Overview

This workflow takes a partially complete Confluence release notes page (with ticket list) and automatically:
1. Finds the Confluence page for the version
2. Extracts all ticket references
3. Reads full ticket details from Jira
4. Categorizes tickets (features, bugs, improvements, etc.)
5. Writes summaries for each section
6. Updates the Confluence page with complete notes

---

## Prerequisites

- Release notes page exists in Confluence (can be template)
- Page contains list of ticket keys (ECD-123, ECD-456, etc.)
- Access to Jira for ticket details
- Access to Confluence for page updates

---

## Step-by-Step Process

### Step 1: Find Release Notes Page

**Search Confluence for version-specific page:**

```bash
# Using Confluence CLI
./scripts/atlassian-cli/confluence-cli search "title ~ 'v5.5.4' OR text ~ 'v5.5.4'" --limit 10
```

**Or using Atlassian MCP (when available):**
```
Search Confluence: "v5.5.4 release notes"
Filter: space = ECD, type = page
```

**Expected Output:**
- Page ID
- Page title
- Space key
- URL

**Documentation Notes:**
> Started by searching Confluence for the version number. Found page ID 123456 titled "Release Notes v5.5.4" in space ECD.

---

### Step 2: Read Page Content

**Retrieve full page content:**

```bash
./scripts/atlassian-cli/confluence-cli page get <page_id>
```

**Parse for:**
- Section headers (Features, Bug Fixes, Improvements, etc.)
- Ticket references (ECD-XXX pattern)
- Existing content vs. placeholders
- Template structure

**Example Page Structure:**
```markdown
# Release Notes v5.5.4
Release Date: 2025-10-25

## Tickets Included
- ECD-123
- ECD-456
- ECD-789

## Features
[To be filled]

## Bug Fixes
[To be filled]

## Improvements
[To be filled]

## Technical Details
[To be filled]
```

**Documentation Notes:**
> Retrieved page content. Found 15 tickets listed. Sections are templated and need to be filled with summaries.

---

### Step 3: Extract All Ticket Keys

**Regex pattern:** `ECD-\d+`

**Extract from:**
- Main ticket list section
- Any inline mentions
- Links in the page

**Create ticket list:**
```python
tickets = ["ECD-123", "ECD-456", "ECD-789", ...]
```

**Documentation Notes:**
> Extracted 15 unique ticket keys from page content using regex pattern.

---

### Step 4: Fetch Ticket Details from Jira

**For each ticket, retrieve:**
- Summary
- Description
- Issue type (Story, Bug, Task, Improvement)
- Priority
- Status (must be Done/Closed for release)
- Components
- Labels
- Comments (for context)
- Linked tickets (dependencies, relates to)

```bash
# Using Jira CLI
for ticket in ECD-123 ECD-456 ECD-789; do
  ./scripts/atlassian-cli/jira-cli issue get $ticket --json > tickets/${ticket}.json
done
```

**Or batch with JQL:**
```bash
./scripts/atlassian-cli/jira-cli search "key in (ECD-123, ECD-456, ECD-789)" --json
```

**Documentation Notes:**
> Fetched full details for all 15 tickets via Jira API. All tickets are in Done status, ready for release.

---

### Step 5: Categorize Tickets

**Group by Issue Type:**

- **Features (Story, Epic):** New capabilities or major enhancements
- **Bug Fixes (Bug):** Defects resolved
- **Improvements (Improvement, Task):** Performance, UX, or minor enhancements
- **Technical/Infrastructure:** Backend changes, dependencies, tooling

**Additional categorization:**
- **User-Facing:** Changes visible to end users
- **Internal:** Developer/admin-only changes
- **Breaking Changes:** Requires migration or config changes

**Example categorization:**
```python
categories = {
    "Features": [
        {"key": "ECD-123", "summary": "Add PDF auto-linking", "priority": "High"},
        {"key": "ECD-456", "summary": "Guest user sharing", "priority": "High"}
    ],
    "Bug Fixes": [
        {"key": "ECD-789", "summary": "Fix login timeout issue", "priority": "Critical"}
    ],
    "Improvements": [
        {"key": "ECD-234", "summary": "Optimize search performance", "priority": "Medium"}
    ]
}
```

**Documentation Notes:**
> Categorized tickets: 5 features, 7 bug fixes, 3 improvements. Identified 2 breaking changes requiring migration notes.

---

### Step 6: Write Summaries for Each Ticket

**Summary Format:**
```markdown
**[ECD-123] Add PDF Auto-Linking**
- Automatically link references within PDFs to Evidence Cloud citations
- Users can now click linked text in uploaded PDFs to navigate directly to sources
- Supports both user-uploaded and system-generated PDFs
- Improves workflow efficiency for literature review
```

**Guidelines:**
- **First line:** Ticket key + summary in bold
- **Bullet points:** What changed, why it matters, user impact
- **User-centric language:** Avoid technical jargon for user-facing features
- **Technical details:** Include for developer/admin changes
- **Links:** Reference documentation, migration guides if needed

**For Bug Fixes:**
```markdown
**[ECD-789] Fix Login Timeout Issue**
- Resolved issue where users were logged out unexpectedly after 5 minutes
- Session timeout now correctly extends to 30 minutes as configured
- Affects all users on SSO authentication
```

**For Technical Changes:**
```markdown
**[ECD-345] Upgrade Django to 4.2 LTS**
- Updated Django framework from 3.2 to 4.2 (LTS release)
- Improves security, performance, and long-term support
- No user-facing changes
- Migration guide: [link]
```

**Documentation Notes:**
> Wrote user-friendly summaries for all 15 tickets. Added migration notes for 2 breaking changes.

---

### Step 7: Generate Full Release Notes Content

**Compile all sections:**

```markdown
# Release Notes v5.5.4
**Release Date:** October 25, 2025
**Release Type:** Minor Release

## Overview
This release includes significant improvements to PDF handling, resolves critical authentication issues, and introduces guest user sharing capabilities. A total of 15 tickets were completed.

## Highlights
- 🚀 **PDF Auto-Linking:** Automatically link references in PDFs to citations
- 👥 **Guest User Sharing:** Share projects with external collaborators
- 🐛 **Login Timeout Fix:** Resolved session timeout issues affecting SSO users

## Features

**[ECD-123] Add PDF Auto-Linking**
- Automatically link references within PDFs to Evidence Cloud citations
- Users can now click linked text in uploaded PDFs to navigate directly to sources
- Supports both user-uploaded and system-generated PDFs
- Improves workflow efficiency for literature review

**[ECD-456] Guest User Sharing**
- Share projects with external collaborators without requiring full accounts
- Guest users have read-only access with configurable permissions
- Email invitations with time-limited access tokens
- Audit logging for all guest user actions

... [continue for all features]

## Bug Fixes

**[ECD-789] Fix Login Timeout Issue**
- Resolved issue where users were logged out unexpectedly after 5 minutes
- Session timeout now correctly extends to 30 minutes as configured
- Affects all users on SSO authentication

... [continue for all bugs]

## Improvements

**[ECD-234] Optimize Search Performance**
- Search queries now return results 3x faster on large datasets
- Improved indexing for full-text search
- Reduced memory usage during complex queries

... [continue for all improvements]

## Technical Details

**Infrastructure:**
- Upgraded Django to 4.2 LTS
- Updated dependencies: requests 2.31.0, celery 5.3.0
- Database schema changes (auto-migrated)

**Breaking Changes:**
⚠️ **API Endpoint Changes:**
- `/api/v1/projects/` renamed to `/api/v2/projects/`
- Old endpoint deprecated, will be removed in v6.0.0
- Migration guide: https://docs.citemed.com/migration/v5.5.4

**Developer Notes:**
- New environment variable required: `PDF_AUTOLINKING_ENABLED`
- Run migrations: `python manage.py migrate`
- Clear cache: `python manage.py clear_cache`

## Upgrade Instructions

1. Backup database before upgrading
2. Pull latest code: `git pull origin v5.5.4`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Collect static files: `python manage.py collectstatic`
6. Restart application: `systemctl restart citemed-web`

## Known Issues
- [ECD-999] Minor UI glitch in dark mode (scheduled for v5.5.5)
- [ECD-888] Performance degradation with >10,000 PDFs (investigating)

## Credits
Special thanks to the development team:
- Mohamed - PDF auto-linking implementation
- Ahmed - Guest user sharing feature
- Thanh - Performance optimizations
- Valentin - Bug fixes and testing
- Josh - Infrastructure upgrades

## Support
For questions or issues, contact:
- Support: support@citemed.com
- Documentation: https://docs.citemed.com/v5.5.4
- Jira Project: https://citemed.atlassian.net/browse/ECD
```

**Documentation Notes:**
> Generated complete release notes with all sections filled. Total length: ~500 lines. Ready for Confluence update.

---

### Step 8: Update Confluence Page

**Using Confluence CLI:**

```bash
# Save content to file
cat > release_notes_v5.5.4.html << 'EOF'
<h1>Release Notes v5.5.4</h1>
<p><strong>Release Date:</strong> October 25, 2025</p>
...
EOF

# Update Confluence page
./scripts/atlassian-cli/confluence-cli page update <page_id> \
  --content "$(cat release_notes_v5.5.4.html)"
```

**Or using Atlassian MCP:**
```
Update Confluence page ID 123456 with content from file
```

**Verify update:**
1. Retrieve page again to confirm changes
2. Check page version incremented
3. Verify formatting renders correctly
4. Share link with team for review

**Documentation Notes:**
> Successfully updated Confluence page. Page version incremented from 12 to 13. Shared link with team for review.

---

## Automation Script

Create `scripts/generate_release_notes.py`:

```python
#!/usr/bin/env python3
"""
Generate release notes from Jira tickets for a Confluence page.

Usage:
  python scripts/generate_release_notes.py v5.5.4
  python scripts/generate_release_notes.py v5.5.4 --confluence-page-id 123456
  python scripts/generate_release_notes.py v5.5.4 --dry-run
"""

import sys
import argparse
import subprocess
import json
import re
from typing import List, Dict, Any

def search_confluence_page(version: str) -> Dict[str, Any]:
    """Search Confluence for release notes page."""
    print(f"🔍 Searching Confluence for '{version}' release notes...")

    cmd = [
        "./scripts/atlassian-cli/confluence-cli",
        "search",
        f"title ~ '{version}' AND type = page",
        "--limit", "10"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse output and return page details
    # (Implementation details)

def get_page_content(page_id: str) -> str:
    """Retrieve Confluence page content."""
    print(f"📄 Retrieving page content for ID {page_id}...")

    cmd = [
        "./scripts/atlassian-cli/confluence-cli",
        "page", "get", page_id
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def extract_ticket_keys(content: str) -> List[str]:
    """Extract all ECD-XXX ticket keys from content."""
    print(f"🎫 Extracting ticket keys...")

    pattern = r'ECD-\d+'
    tickets = list(set(re.findall(pattern, content)))
    print(f"   Found {len(tickets)} unique tickets")
    return tickets

def fetch_ticket_details(ticket_keys: List[str]) -> List[Dict[str, Any]]:
    """Fetch full details for all tickets from Jira."""
    print(f"📥 Fetching details for {len(ticket_keys)} tickets...")

    jql = f"key in ({','.join(ticket_keys)})"

    cmd = [
        "./scripts/atlassian-cli/jira-cli",
        "search",
        jql,
        "--json"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data.get('issues', [])

def categorize_tickets(tickets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize tickets by type."""
    print(f"📊 Categorizing tickets...")

    categories = {
        "Features": [],
        "Bug Fixes": [],
        "Improvements": [],
        "Technical": []
    }

    for ticket in tickets:
        issue_type = ticket['fields']['issuetype']['name']

        if issue_type in ['Story', 'Epic']:
            categories['Features'].append(ticket)
        elif issue_type == 'Bug':
            categories['Bug Fixes'].append(ticket)
        elif issue_type in ['Improvement', 'Enhancement']:
            categories['Improvements'].append(ticket)
        else:
            categories['Technical'].append(ticket)

    for category, items in categories.items():
        print(f"   {category}: {len(items)} tickets")

    return categories

def generate_ticket_summary(ticket: Dict[str, Any]) -> str:
    """Generate markdown summary for a single ticket."""
    key = ticket['key']
    summary = ticket['fields']['summary']
    description = ticket['fields'].get('description', {})

    # Extract description text from ADF format
    desc_text = extract_description_text(description)

    # Generate bullet points based on description
    bullets = generate_bullet_points(desc_text)

    summary_md = f"**[{key}] {summary}**\n"
    for bullet in bullets:
        summary_md += f"- {bullet}\n"

    return summary_md

def extract_description_text(description: Dict) -> str:
    """Extract plain text from Atlassian Document Format."""
    if not description or 'content' not in description:
        return ""

    text = []
    for block in description['content']:
        if block.get('type') == 'paragraph':
            for item in block.get('content', []):
                if item.get('type') == 'text':
                    text.append(item.get('text', ''))

    return ' '.join(text)

def generate_bullet_points(description: str) -> List[str]:
    """Generate user-friendly bullet points from description."""
    # Simple implementation - split by sentences
    # More sophisticated version could use AI/LLM for summarization
    sentences = description.split('. ')
    return [s.strip() + '.' for s in sentences[:3] if s.strip()]

def generate_release_notes(
    version: str,
    categories: Dict[str, List[Dict[str, Any]]]
) -> str:
    """Generate complete release notes markdown."""
    print(f"✍️  Generating release notes...")

    notes = f"# Release Notes {version}\n\n"

    # Overview
    total_tickets = sum(len(tickets) for tickets in categories.values())
    notes += f"**Total Changes:** {total_tickets} tickets\n\n"

    # Each category
    for category, tickets in categories.items():
        if not tickets:
            continue

        notes += f"## {category}\n\n"

        for ticket in tickets:
            notes += generate_ticket_summary(ticket)
            notes += "\n"

    return notes

def update_confluence_page(page_id: str, content: str, dry_run: bool = False):
    """Update Confluence page with generated notes."""
    if dry_run:
        print(f"🔍 DRY RUN - Would update page {page_id}")
        print("\n" + "="*60)
        print(content)
        print("="*60)
        return

    print(f"📝 Updating Confluence page {page_id}...")

    # Convert markdown to HTML (simplified)
    html_content = markdown_to_html(content)

    cmd = [
        "./scripts/atlassian-cli/confluence-cli",
        "page", "update", page_id,
        "--content", html_content
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Successfully updated page!")
    else:
        print(f"❌ Failed to update page: {result.stderr}")

def markdown_to_html(markdown: str) -> str:
    """Convert markdown to Confluence HTML."""
    # Simplified conversion - use proper library in production
    html = markdown.replace('# ', '<h1>').replace('\n\n', '</h1>\n<p>')
    html = html.replace('## ', '<h2>').replace('\n\n', '</h2>\n<p>')
    html = html.replace('**', '<strong>').replace('**', '</strong>')
    html = html.replace('- ', '<li>').replace('\n', '</li>\n')
    return html

def main():
    parser = argparse.ArgumentParser(description='Generate release notes')
    parser.add_argument('version', help='Version number (e.g., v5.5.4)')
    parser.add_argument('--confluence-page-id', help='Confluence page ID')
    parser.add_argument('--dry-run', action='store_true', help='Preview without updating')

    args = parser.parse_args()

    print("="*60)
    print(f"🚀 Release Notes Generator - {args.version}")
    print("="*60)

    # Step 1: Find Confluence page
    if args.confluence_page_id:
        page_id = args.confluence_page_id
    else:
        page_data = search_confluence_page(args.version)
        page_id = page_data['id']

    # Step 2: Get page content
    content = get_page_content(page_id)

    # Step 3: Extract tickets
    ticket_keys = extract_ticket_keys(content)

    # Step 4: Fetch ticket details
    tickets = fetch_ticket_details(ticket_keys)

    # Step 5: Categorize tickets
    categories = categorize_tickets(tickets)

    # Step 6: Generate release notes
    notes = generate_release_notes(args.version, categories)

    # Step 7: Update Confluence
    update_confluence_page(page_id, notes, dry_run=args.dry_run)

    print("\n✅ Release notes generation complete!")

if __name__ == '__main__':
    main()
```

**Usage:**
```bash
# Preview release notes
python scripts/generate_release_notes.py v5.5.4 --dry-run

# Generate and update Confluence
python scripts/generate_release_notes.py v5.5.4

# Specify page ID manually
python scripts/generate_release_notes.py v5.5.4 --confluence-page-id 123456
```

---

## Self-Documentation Log

**Process Discovery Notes:**

1. **Search Strategy:**
   - Initially searched by title, but some pages use different naming conventions
   - Better to search by content containing version number
   - Need to handle multiple matches (choose most recent)

2. **Ticket Extraction:**
   - Simple regex works well for ticket keys
   - Need to deduplicate (same ticket may appear multiple times)
   - Consider checking if tickets are actually in "Done" status

3. **Categorization Challenges:**
   - Issue type doesn't always match user-facing category
   - Some "Tasks" are actually features
   - Need manual review for edge cases

4. **Summary Writing:**
   - Descriptions vary widely in quality
   - Some tickets lack descriptions entirely
   - May need to read comments for context
   - AI/LLM could help generate better summaries

5. **Formatting:**
   - Confluence uses storage format (HTML-like)
   - Need proper conversion from markdown
   - Consider using Confluence macros for better formatting

6. **Verification:**
   - Always preview changes before updating
   - Get team review before publishing
   - Keep backup of original page content

---

## Future Enhancements

1. **AI-Powered Summarization:**
   - Use LLM to write better ticket summaries
   - Extract key points from descriptions and comments
   - Generate user-friendly language automatically

2. **Automatic Screenshots:**
   - Embed screenshots from tickets
   - Pull images from linked PRs
   - Generate before/after comparisons

3. **Impact Analysis:**
   - Analyze code changes to assess impact
   - Identify breaking changes automatically
   - Generate migration guides

4. **Multi-Language Support:**
   - Generate release notes in multiple languages
   - Translate technical terms appropriately

5. **Distribution:**
   - Auto-post to Slack channels
   - Email to stakeholders
   - Generate PDF version

---

## Related Documents

- `.claude/agents/jira-manager.md` - Jira operations
- `.claude/skills/jira-best-practices.md` - Jira query optimization
- `scripts/atlassian-cli/README.md` - CLI tool usage
- `.claude/FUTURE_WORK.md` - Long-term improvements

---

**Status:** ⏳ Workflow defined, ready for implementation
**Next Step:** Test with v5.5.4 release notes using Atlassian CLI
