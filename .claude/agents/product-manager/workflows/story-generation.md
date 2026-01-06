# Story Generation Workflow

This workflow guides Claude Code through generating comprehensive user stories from conversation context.

## When to Use This Workflow

Triggered when a user mentions @remington with requests like:
- "Can you create a story for this feature?"
- "Write up a ticket for this functionality"
- "Add this as a new feature"
- "Create a user story for..."

## Step 1: Analyze Request Context

### Extract Key Information

**User Intent:**
- What capability does the user want to add?
- What problem does this solve?
- Who is the target user (persona)?

**Technical Context:**
- Which module/area of CiteMed is affected? (CiteSource, Literature, Dashboard)
- Is there existing similar functionality?
- What are the integration points?

**Business Context:**
- Why is this valuable?
- What customer pain point does it address?
- What are the expected outcomes?

### Identify Scope

**Simple Story** (1-2 days):
- Single component change
- Well-defined requirements
- No major integrations

**Complex Story** (3-5 days):
- Multiple components
- New data models
- External integrations
- Multi-phase approach needed

**Epic Candidate** (>1 week):
- Strategic initiative
- Multiple related features
- Affects multiple modules
- Should be broken into stories

## Step 2: Gather Context from Platform

### Review Existing Implementation

Search for similar functionality:
```
Use Grep tool to search citemed_web for:
- Similar feature names
- Related model names
- Comparable UI patterns
```

### Check Related Tickets

Search Jira for:
- Recently completed similar features
- Dependencies or blockers
- Related bugs or technical debt

### Understand Data Model

Check UML documentation:
- What models already exist that can be reused?
- What new models are needed?
- What relationships exist?

## Step 3: Load Story Template

Load `.claude/agents/product-manager/templates/story-template.md`

This template includes:
- Title
- User Story Statement (As a... I want... So that...)
- Business Context
- Technical Scope
- Acceptance Criteria
- Implementation Notes
- Definition of Done

## Step 4: Generate Comprehensive Story

### Craft Clear Title

Format: `[Action] [Object/Feature] with [Key Capability]`

**Good Examples:**
- "Search Project References and Insert Inline Citation with Style Control"
- "Bulk Import References from EndNote with Deduplication"
- "Export Literature Review Results to CSV with Custom Fields"

**Avoid Vague Titles:**
- ❌ "Add search feature"
- ❌ "Improve references"
- ❌ "New functionality"

### Write User Story Statement

Follow the structure:
```
**As a** [specific persona with role]
**I want** [clear capability description]
**So that** [specific outcome or benefit]
```

**Example:**
```
**As a** regulatory affairs specialist managing a product dossier
**I want** to bulk import references from my EndNote library with automatic deduplication
**So that** I can quickly populate my project with existing research without manual entry or duplicates
```

### Define Business Context

**Target Persona:**
- Who is the primary user?
- What is their current workflow?
- What pain points will this eliminate?

**Customer Impact:**
- Quantify time savings (e.g., "Reduces citation insertion from 2 minutes to 10 seconds")
- Error reduction (e.g., "Eliminates manual formatting errors")
- Workflow improvement (e.g., "Removes context switching between applications")

### Specify Technical Scope

**Core Functionality:**
Describe what will be built in 2-3 detailed paragraphs

**API Requirements:**
- List new endpoints needed
- Describe request/response formats
- Specify performance targets (e.g., "< 500ms response time")

**Integration Points:**
- What systems does this connect to?
- What external APIs are needed?
- What database changes are required?

### Write Acceptance Criteria

Make criteria **testable** and **specific**:

**Good Criteria:**
- ✅ "User can upload an EndNote XML file up to 10MB"
- ✅ "System detects and flags duplicate references based on DOI and title matching"
- ✅ "Progress indicator shows during import with % complete"
- ✅ "Error messages clearly explain validation failures with specific field names"

**Avoid Vague Criteria:**
- ❌ "Import works correctly"
- ❌ "User is happy with the feature"
- ❌ "System handles errors"

### Add Implementation Notes

**Technical Approach:**
- What architecture pattern to use (Django views, DRF serializers, Vue components)?
- What libraries or frameworks are recommended?
- What caching or optimization strategies?

**Dependencies:**
- What must be completed first?
- What will depend on this being done?
- What external dependencies exist?

### Complete Definition of Done

Ensure checklist includes:
- [ ] All acceptance criteria met and tested
- [ ] Code reviewed and approved
- [ ] Unit tests written and passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed in staging
- [ ] Documentation updated (if API changes)
- [ ] Deployment plan documented (if database migrations)

## Step 5: Handle Multi-Phase Stories

If the story is complex (>5 days), break it into phases:

### Phase 1: Foundation/MVP
What is the minimum viable functionality?
- Core user workflow completion
- Basic error handling
- Essential validations

### Phase 2: Enhanced Features
What makes it production-ready?
- Performance optimizations
- Advanced error handling
- Edge case coverage
- UI polish

### Phase 3: Advanced/Future
What are nice-to-have features?
- Advanced customization
- Additional integrations
- Analytics and reporting

## Step 6: Post Draft for Approval

Format the response to the original comment:

```markdown
📋 I've analyzed your request and created a draft user story.

---

# Story: [Title]

## User Story Statement
**As a** [persona]
**I want** [capability]
**So that** [outcome]

## Business Context

[Business context sections...]

## Technical Scope

[Technical scope sections...]

## Acceptance Criteria

[Numbered checklist...]

## Implementation Notes

[Implementation guidance...]

---

**Next Steps:**
- Reply **'approved'** to create Jira ticket ECD-XXX
- Reply **'changes: [your feedback]'** to refine the story
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
    request_type='story',
    user_id='user_account_id',
    user_name='User Display Name',
    original_context='Original comment text...',
    draft_content='Full formatted story markdown...'
)
```

## Quality Checklist

Before posting the draft, verify:

✓ **User Value is Clear**
- Business context explains why this matters
- Customer impact is quantified
- Pain points are specific

✓ **Technical Approach is Detailed**
- API requirements are specific (endpoints, formats)
- Data models are identified or defined
- Performance targets are stated

✓ **Acceptance Criteria are Testable**
- Each criterion can be verified
- Edge cases are covered
- Error scenarios are included

✓ **Scope is Right-Sized**
- Story fits within 1 sprint (≤5 days)
- If larger, multi-phase breakdown is provided
- Dependencies are identified

✓ **Platform Context is Applied**
- Existing CiteMed patterns are followed
- Similar features are referenced
- Regulatory/compliance needs are considered

## Common Patterns for CiteMed Stories

### Reference Management Features
- Always consider deduplication logic
- Include audit trail requirements
- Handle bulk operations with progress indicators
- Support export in multiple formats

### Literature Review Features
- Systematic review workflow alignment
- Quality assessment integration
- Collaboration and assignment capabilities
- Evidence extraction and tagging

### Reporting Features
- CSV export as minimum
- PDF generation for formal reports
- Customizable field selection
- Date range filtering

### Import/Export Features
- Multiple format support (RIS, EndNote XML, CSV)
- Preview before final import
- Rollback capability for bulk operations
- Progress tracking for large datasets

## Error Prevention

### Don't Invent Models
❌ Never reference Django models that don't exist
✅ Check `/Users/ethand320/code/citemed/citemed_web/docs/UML_current.mmd` first
✅ If new model needed, document it explicitly as a new model

### Don't Assume Infrastructure
❌ Don't assume services exist (e.g., email server, queue system)
✅ Check existing architecture first
✅ Document new infrastructure needs explicitly

### Don't Skip Edge Cases
❌ Don't write vague criteria like "handles errors"
✅ Specify each error scenario with expected behavior

## Example: Complete Story Generation

**User Request:** "@remington can we create a story for bulk reference import from EndNote?"

**Generated Story:**

```markdown
# Story: Bulk Import References from EndNote XML with Deduplication

## User Story Statement
**As a** regulatory affairs specialist managing multiple product dossiers
**I want** to bulk import references from my EndNote library with automatic deduplication
**So that** I can quickly populate my project with existing research without manual data entry or duplicate references

## Business Context

### Target Persona
- **Primary User:** Regulatory Affairs Specialist with 100-1000 references per project
- **Current Workflow:** Manual one-by-one reference creation or CSV import requiring cleanup
- **Pain Points:** Time-consuming data entry, frequent duplicates, formatting inconsistencies

### Customer Impact
- **Time Savings:** Reduces project setup from 2-3 hours to 5 minutes for 100 references
- **Error Reduction:** Eliminates manual entry errors and duplicate references
- **Workflow Improvement:** Enables seamless migration from EndNote to CiteMed

## Technical Scope

### Core Functionality
Implement a file upload interface that accepts EndNote XML files (up to 10MB). Parse the XML structure to extract reference metadata (authors, title, publication year, DOI, abstract, etc.). Apply deduplication logic based on DOI (primary) and title+year (fallback). Display preview of references to be imported with duplicate warnings. Allow user to review and confirm import, then create Reference objects in batch with progress indicator.

### API Requirements
- **Endpoint:** `POST /api/projects/{project_id}/references/import/endnote`
- **Request:** Multipart form data with EndNote XML file
- **Response:** `{ "preview": [...], "duplicates": [...], "new_references": count }`
- **Performance Target:** < 2 seconds for 100 references

### Integration Points
- **System Dependencies:** CiteSource reference management module
- **External APIs:** None (local XML parsing)
- **Database Changes:** No schema changes, uses existing Reference model

## Acceptance Criteria

### Functional Requirements
- [ ] User can upload EndNote XML file (formats X7-X20 supported)
- [ ] System parses and extracts: authors, title, year, DOI, journal, abstract, keywords
- [ ] Duplicate detection checks: exact DOI match OR (title similarity >90% AND same year)
- [ ] Preview screen shows: total references, new references, duplicates (with conflict resolution)
- [ ] User can select: "Import all new", "Skip duplicates", or "Review each"
- [ ] Progress indicator shows during import with estimated time remaining
- [ ] Success message reports: X references imported, Y duplicates skipped
- [ ] Error handling: Invalid XML format shows clear error with example
- [ ] Error handling: File size >10MB shows clear size limit message
- [ ] Import is atomic: either all succeed or all rollback on error

## Implementation Notes

### Technical Approach
- **Parser:** Use Python `xml.etree.ElementTree` for EndNote XML parsing
- **Deduplication:** Implement in `utils/reference_deduplication.py` with configurable thresholds
- **Progress:** Use Django Channels for real-time progress updates to frontend
- **UI:** Add "Import from EndNote" button to Project References page

### Dependencies
- **Upstream:** None (uses existing Reference model)
- **Downstream:** This unblocks "Bulk Import from RIS" story (similar pattern)
- **External:** None

## Definition of Done

- [ ] All acceptance criteria met and tested
- [ ] Code reviewed and approved
- [ ] Unit tests for XML parsing (>85% coverage)
- [ ] Integration tests for full import workflow
- [ ] Manual testing with real EndNote XML files from 3 customers
- [ ] Error scenarios tested (corrupt XML, huge files, edge cases)
- [ ] User documentation updated with import instructions
```

This story is comprehensive, testable, and ready for development.

---

**Remember:** The goal is to create stories that developers can implement with confidence, without needing to come back for clarification.
