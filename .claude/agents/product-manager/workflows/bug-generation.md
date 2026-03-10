# Bug Report Generation Workflow

This workflow guides Claude Code through generating comprehensive bug reports from user descriptions or observations.

## When to Use This Workflow

Triggered when a user mentions @remington with requests like:
- "Can you create a bug report for this?"
- "File a bug for this issue"
- "This is broken, write up a ticket"
- "Create a defect report"

## Step 1: Analyze the Bug Report

### Extract Core Information

**Problem Description:**
- What is broken or not working as expected?
- When does the issue occur?
- Is it consistently reproducible or intermittent?

**User Impact:**
- Who is affected? (specific personas or all users)
- How many users are impacted?
- Is there a workaround available?

**System Context:**
- Which module/component is affected?
- What browser/platform/environment?
- When was this first observed?

## Step 2: Assess Severity

Use the 4-level severity matrix:

### Critical
- **System unusable** - Core functionality completely broken
- **Data loss** - User data is being corrupted or lost
- **Security issue** - Authentication bypass, data exposure
- **No workaround** - Users cannot accomplish their task at all

**Examples:**
- Login system completely down
- References being deleted unintentionally
- User data visible to other users

### High
- **Major feature broken** - Key functionality not working
- **Significant user impact** - Affects many users or critical workflows
- **Workaround exists but difficult** - Users can work around but with significant effort

**Examples:**
- Search returns no results
- PDF export fails for all documents
- Citation insertion doesn't work in Word

### Medium
- **Feature partially broken** - Works in some cases, fails in others
- **Moderate impact** - Affects subset of users or less critical workflows
- **Workaround available** - Reasonable alternative exists

**Examples:**
- Search works but misses some results
- Export works but formatting is incorrect
- Some citation styles fail to render

### Low
- **Minor issue** - Cosmetic problem or minor inconvenience
- **Minimal impact** - Rare edge case or minor usability issue
- **Easy workaround** - Simple alternative available

**Examples:**
- UI element slightly misaligned
- Tooltip text has typo
- Non-critical validation message unclear

## Step 3: Load Bug Template

Load `.claude/agents/product-manager/templates/bug-template.md`

This template includes:
- Title
- Summary
- Steps to Reproduce
- Expected vs Actual Behavior
- Environment
- Impact Assessment
- Technical Details
- Acceptance Criteria

## Step 4: Generate Comprehensive Bug Report

### Craft Clear Title

Format: `Bug: [Concise Description of Issue]`

**Good Examples:**
- "Bug: Reference Search Fails for Users with Special Characters in Names"
- "Bug: PDF Export Timeout for Documents Over 100 Pages"
- "Bug: Citation Style Dropdown Empty After Recent Update"

**Avoid Vague Titles:**
- ❌ "Bug: Search not working"
- ❌ "Bug: Export issue"
- ❌ "Bug: Problem with citations"

### Write Clear Summary

One-sentence description capturing:
- What is broken
- The specific impact

**Example:**
"Reference search functionality fails when the user's name contains special characters (e.g., accents, hyphens), preventing them from searching their project references."

### Document Reproduction Steps

Make steps **specific** and **ordered**:

**Good Steps:**
```
1. Log in as a user with special characters in name (e.g., "José García-Smith")
2. Navigate to CiteSource > My References
3. Enter "cancer research" in the reference search box
4. Click the Search button
5. Observe the error message
```

**Avoid Vague Steps:**
```
❌ 1. Go to the search page
❌ 2. Try to search
❌ 3. It doesn't work
```

### Specify Expected vs Actual Behavior

Be precise about what should happen vs what does happen:

**Expected Behavior:**
"Search results should display all matching references regardless of special characters in the user's name. Results should be sorted by relevance."

**Actual Behavior:**
"Search returns error message: 'Invalid search request'. No results are displayed. Browser console shows URL encoding error."

### Document Environment

**Key Information:**
- Browser and version (e.g., Chrome 120, Safari 17)
- User role/persona affected
- Module/component (CiteSource, Literature, Dashboard)
- Platform (Web, Word Add-in, Mobile)
- Date first observed

**Example:**
```
- **Browser/Version:** Chrome 120, Firefox 121 (both affected)
- **User Role:** Regulatory Affairs Specialist, Medical Affairs Manager
- **Module:** CiteSource Reference Search
- **Platform:** Web application
- **Date First Observed:** 2025-11-10 (after deployment of ECD-456)
```

### Assess Impact

**Severity Selection:**
Choose the appropriate level and justify it

**Users Affected:**
Be specific about the scope:
- "All users" vs "~15% of users"
- "Enterprise customers only" vs "All subscription tiers"
- "Safari users" vs "All browsers"

**Workaround:**
If available, document clearly:
```
- **Available:** Yes
- **Description:** Users can navigate to "All References" and manually scroll to find references. This adds ~5 minutes per search operation.
```

Or if not:
```
- **Available:** No
- **Description:** Search functionality is completely unavailable for affected users.
```

### Gather Technical Details

**Error Messages:**
Include exact error text from UI and console:
```javascript
Console Error:
Uncaught TypeError: Cannot read property 'normalize' of undefined
  at searchReferences (SearchComponent.vue:145)
  at onClick (SearchComponent.vue:89)
```

**Related Components:**
Identify affected code areas:
- **Affected Models:** `Reference`, `UserProfile`
- **Affected Views/API Endpoints:** `/api/references/search/`
- **Affected Frontend Components:** `SearchComponent.vue`, `ReferenceList.vue`
- **Database Tables:** `references_reference`, `auth_user`

**Potential Cause:**
If known or suspected:
"The search API endpoint may not be properly URL-encoding user profile data when building the search query. Special characters in the user's name field could be causing the URL encoding to fail."

### Write Acceptance Criteria

Bug fix verification should be specific:

**Good Criteria:**
- [ ] Bug is reproducible in test environment before fix
- [ ] Search works correctly for users with accented characters (é, ñ, ü, etc.)
- [ ] Search works correctly for users with hyphens and apostrophes in names
- [ ] Search works correctly for users with Asian/Cyrillic characters
- [ ] Existing search functionality for users without special characters remains unaffected
- [ ] Unit tests added covering special character edge cases
- [ ] Manual testing completed with 5 real user accounts with special characters

**Avoid Vague Criteria:**
- ❌ "Bug is fixed"
- ❌ "Search works"
- ❌ "No more errors"

## Step 5: Link Related Context

### Related Tickets
Search Jira for:
- Similar bugs recently reported
- Original implementation ticket (if regression)
- Related feature work in progress

### Related Code Changes
Check git history:
- Recent commits to affected components
- Recent deployments that might have introduced the bug

## Step 6: Post Draft for Approval

Format the response to the original comment:

```markdown
📋 I've analyzed the issue and created a draft bug report.

---

# Bug: [Title]

## Summary
[One-sentence description]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- **Browser/Version:** [Details]
- **User Role:** [Persona]
- **Module:** [Component]

## Impact
- **Severity:** [Critical/High/Medium/Low]
- **Users Affected:** [Scope]
- **Workaround:** [Yes/No with description]

## Technical Details
[Error messages, potential cause, affected components]

## Acceptance Criteria
- [ ] [Specific testable requirement 1]
- [ ] [Specific testable requirement 2]
[...]

---

**Next Steps:**
- Reply **'approved'** to create Jira bug ticket ECD-XXX
- Reply **'changes: [your feedback]'** to refine the report
- Reply **'cancel'** to discard

I'll monitor this thread for your response.
```

## Step 7: Store Draft in Database

Use the PM requests database:

```python
from src.database.pm_requests_db import get_pm_requests_db

db = get_pm_requests_db()
request_id = db.create_request(
    source='jira',  # or 'slack', 'bitbucket'
    source_id='ECD-123',  # issue key, thread_ts, or pr_id
    request_type='bug',
    user_id='user_account_id',
    user_name='User Display Name',
    original_context='Original comment text describing the bug...',
    draft_content='Full formatted bug report markdown...'
)
```

## Quality Checklist

Before posting the draft, verify:

✓ **Problem is Clearly Described**
- Summary is concise and specific
- Reproduction steps are detailed and ordered
- Expected vs actual behavior is precise

✓ **Severity is Correct**
- Severity level matches impact guidelines
- User impact is quantified
- Workaround availability is documented

✓ **Technical Details are Complete**
- Error messages are included verbatim
- Affected components are identified
- Environment information is specific

✓ **Acceptance Criteria are Testable**
- Each criterion is verifiable
- Edge cases are covered
- Regression prevention is included

✓ **Context is Linked**
- Related tickets are referenced
- Recent code changes are noted
- Original implementation is linked if regression

## Common Bug Patterns in CiteMed

### Data Validation Bugs
- Input sanitization missing
- Special characters not handled
- Edge cases in validation logic
- SQL injection vulnerabilities

### Integration Bugs
- API endpoint failures
- Third-party service timeout
- Database connection issues
- File upload size limits

### UI/UX Bugs
- Browser compatibility issues
- Responsive design breakage
- Accessibility failures
- Performance degradation

### Permission/Security Bugs
- Authorization bypass
- Data visibility issues
- Role-based access failures
- Session management problems

## Severity Escalation Guidelines

### When to Escalate Severity

**Upgrade to Critical if:**
- Initially thought to affect subset, but actually affects all users
- Workaround was identified, but it causes data corruption
- Bug exposes customer data or security vulnerability

**Keep as High/Medium if:**
- Impact is isolated to specific user segment
- Reliable workaround exists
- No data loss or security risk

## Example: Complete Bug Report Generation

**User Request:** "@remington can you create a bug report for this? The reference search isn't working for users with special characters in their names"

**Generated Bug Report:**

```markdown
# Bug: Reference Search Fails for Users with Special Characters in Names

## Summary
Reference search functionality fails when the user's name contains special characters (e.g., accents, hyphens), preventing them from searching their project references and blocking a core workflow.

## Steps to Reproduce
1. Log in as a user with special characters in name (test account: "José García-Smith" or "Müller-Böhm")
2. Navigate to CiteSource > My References (or any project references page)
3. Enter any search term in the reference search box (e.g., "cancer research")
4. Click the Search button or press Enter
5. Observe error message and console output

## Expected Behavior
Search results should display all matching references from the user's projects, sorted by relevance. Special characters in the user's name should not affect search functionality.

## Actual Behavior
Search returns error message: "Invalid search request. Please try again."
No results are displayed.
Browser console shows:
```
URIError: URI malformed
  at decodeURIComponent (<anonymous>)
  at buildSearchQuery (search-api.js:45)
  at performSearch (ReferenceSearch.vue:123)
```

## Environment
- **Browser/Version:** Chrome 120, Firefox 121, Safari 17 (all affected)
- **User Role:** Regulatory Affairs Specialist, Medical Affairs Manager (any authenticated user)
- **Module:** CiteSource Reference Search
- **Platform:** Web application
- **Date First Observed:** 2025-11-10 (reported by 3 users; first deployment: ECD-456 on 2025-11-09)

## Impact

### Severity
**High** - Major feature broken, affecting ~15% of users, workaround available but time-consuming

### Users Affected
- **Number/Percentage:** Approximately 15% of users (80 out of 530 active users have special characters in names)
- **User Segment:** Users with non-ASCII characters in their names (accents, umlauts, hyphens, apostrophes)

### Workaround
- **Available:** Yes
- **Description:** Users can navigate to "All References" view and manually scroll or use browser find (Ctrl+F) to locate references. This adds ~5 minutes per search operation and doesn't support advanced filtering.

## Technical Details

### Error Messages
Browser Console:
```javascript
URIError: URI malformed
  at decodeURIComponent (<anonymous>)
  at buildSearchQuery (search-api.js:45)
  at performSearch (ReferenceSearch.vue:123)

API Response (Status 400):
{
  "error": "Invalid search parameters",
  "detail": "URL encoding error in user context"
}
```

### Related Components
- **Affected Models:** `UserProfile` model (name field used in search context)
- **Affected Views/API Endpoints:** `GET /api/references/search/?q={query}&user={user_id}`
- **Affected Frontend Components:** `ReferenceSearch.vue` (line 123), `search-api.js` (line 45)
- **Database Tables:** `auth_user` (name fields), `references_reference`

### Potential Cause
The search API endpoint constructs search queries using the user's display name as part of the request context. When the name contains special characters (non-ASCII), the URL encoding fails because `decodeURIComponent()` is called on already-decoded UTF-8 strings, causing a double-decoding error.

Likely root cause: Recent refactor in ECD-456 changed how user context is passed to search endpoint, introducing this regression.

### Related Tickets
- ECD-456: "Refactor search API for performance improvements" (deployed 2025-11-09)
- ECD-234: Original search implementation (2025-08-15)

## Acceptance Criteria

### Bug Fix Verification
- [ ] Bug is reproducible in test environment with affected user accounts before fix
- [ ] Search works correctly for users with accented characters (é, ñ, ü, ç, à, etc.)
- [ ] Search works correctly for users with hyphens in names (e.g., "García-Smith")
- [ ] Search works correctly for users with apostrophes in names (e.g., "O'Brien")
- [ ] Search works correctly for users with Asian characters (Japanese, Chinese, Korean)
- [ ] Search works correctly for users with Cyrillic characters (Russian, Ukrainian)
- [ ] Existing search functionality for ASCII-only names remains unaffected (no regression)
- [ ] Search performance remains within acceptable range (< 500ms response)

### Testing Requirements
- [ ] Unit tests added for URL encoding with special characters (>10 test cases)
- [ ] Integration tests cover full search workflow with special character names
- [ ] Manual testing completed with 5+ real user accounts with various special characters
- [ ] Tested across all supported browsers (Chrome, Firefox, Safari, Edge)
- [ ] Load testing confirms no performance degradation

### Documentation
- [ ] Root cause documented in this ticket with code references
- [ ] Fix approach documented with code examples
- [ ] Release notes updated for customer communication (if High severity)

## Additional Context

### Customer Reports
- 3 support tickets received (2025-11-10 to 2025-11-11)
- Customers: PharmaX, MedDevice Corp, BioPharma Solutions
- All reported after deployment of ECD-456 (2025-11-09)

### Sample User Accounts for Testing
- Test account 1: josé.garcia-smith@example.com (Name: "José García-Smith")
- Test account 2: anna.mueller@example.com (Name: "Anna Müller-Böhm")
- Test account 3: marie.obrien@example.com (Name: "Marie O'Brien")

```

This bug report is comprehensive, actionable, and includes all information developers need to reproduce, fix, and verify the bug.

---

**Remember:** A good bug report saves hours of back-and-forth by providing all necessary information up front.
