# Epic Generation Workflow

This workflow guides Claude Code through generating comprehensive epics from high-level strategic initiatives or themes.

## When to Use This Workflow

Triggered when a user mentions @remington with requests like:
- "Create an epic for this initiative"
- "This should be an epic, not a story"
- "Write up an epic for this strategic theme"
- "Make this into an epic with multiple stories"

## Step 1: Analyze the Initiative

### Identify Strategic Nature

**Epic Indicators:**
- Spans multiple sprints (typically > 2 weeks)
- Requires multiple stories to complete
- Represents a strategic business initiative
- Affects multiple system components or modules
- Has measurable business impact (revenue, compliance, market positioning)

**Business Value:**
- What market opportunity does this address?
- What competitive advantage does it create?
- What customer pain points does it solve at scale?
- What regulatory/compliance needs does it meet?

**Scope Assessment:**
- How many user-facing features are involved?
- What system integrations are required?
- What new infrastructure or capabilities are needed?
- Can this be broken into logical phases?

## Step 2: Gather Strategic Context

### Research Market Position

**Questions to Answer:**
- Is this addressing a customer request from multiple sources?
- Does this close a competitive gap?
- Is there a compliance or regulatory driver?
- What's the revenue/retention impact?

### Identify Dependencies

**Technical Dependencies:**
- What infrastructure must exist first?
- What third-party integrations are needed?
- What platform capabilities are required?

**Business Dependencies:**
- What customer commitments drive timing?
- What regulatory deadlines exist?
- What product roadmap dependencies?

## Step 3: Load Epic Template

Load `.claude/agents/product-manager/templates/epic-template.md`

This template includes:
- Title (strategic theme)
- Business Justification
- Scope Overview
- Success Criteria
- Timeline Expectations
- Related Resources

## Step 4: Generate Comprehensive Epic

### Craft Strategic Title

Format: `[Strategic Theme or Business Capability]`

**Good Examples:**
- "Multi-Format Reference Import and Export System"
- "Advanced Literature Review Collaboration Platform"
- "AI-Powered Document Analysis and Extraction"
- "Enterprise-Grade Audit Trail and Compliance Reporting"

**Avoid:**
- ❌ "Import/Export Features"
- ❌ "Better Collaboration"
- ❌ "AI Stuff"

### Write Business Justification

#### Strategic Value
- **Market Positioning:** How does this strengthen competitive position?
  - "This epic establishes CiteMed as the only platform supporting all major reference formats, removing the #1 barrier to customer adoption"

- **Customer Impact:** Which customer segments benefit and how?
  - "Enterprise customers with 10,000+ references (40% of potential market) can now migrate to CiteMed without manual data entry"

- **Business Driver:** What's the primary business case?
  - "Revenue growth via enterprise segment expansion" OR
  - "Compliance with new EU MDR requirements" OR
  - "Cost reduction through automation"

#### Customer Pain Points Addressed
List specific, researched pain points:
- "Current manual reference entry takes regulatory teams 40-60 hours per new dossier submission"
- "Lack of EndNote integration causes 70% of trial users to abandon platform"
- "Enterprise customers require RIS/XML import for compliance audit workflows"

#### Competitive Advantages
What differentiators does this create?
- "Only regulatory platform with native EndNote bidirectional sync"
- "First to support automated extraction from ClinicalTrials.gov PDFs"
- "Unique audit trail linking imported references to source files"

### Define Scope Overview

#### Core Functionality Areas
List 3-5 high-level capability clusters:
- "Multi-format import engine (EndNote XML, RIS, BibTeX, PubMed XML)"
- "Automated deduplication and conflict resolution"
- "Bulk export with customizable formatting"
- "Import validation and error reporting"
- "Progress tracking for large imports (10,000+ references)"

#### Integration Points
Major system connections:
- "EndNote Web API for direct library sync"
- "PubMed E-utilities for metadata enrichment"
- "AWS S3 for large file storage and processing"
- "Elasticsearch for fuzzy duplicate detection"

#### Out of Scope
Explicitly exclude to prevent scope creep:
- "Real-time collaborative editing (future phase)"
- "Mobile app import (separate epic)"
- "Mendeley/Zotero import (evaluate market demand first)"

### Set Success Criteria

#### Business Impact Measurements
Quantifiable metrics:
- **Customer Adoption:** "50% of enterprise trial users activate import feature within first 30 days"
- **Usage Metrics:** "Average 500 references imported per enterprise customer onboarding"
- **Customer Satisfaction:** "NPS score +15 points for users who use import vs manual entry"

#### Financial Impact
Business case validation:
- **Revenue Impact:** "$120K ARR increase from 3 large customers blocked on import functionality"
- **Cost Savings:** "Reduce customer onboarding support time from 8 hours to 1 hour per enterprise customer"
- **Market Share:** "Capture 15% of EndNote-using pharma companies (estimated 200 potential customers)"

#### Compliance/Regulatory Benefits
If applicable:
- "Audit trail proves reference provenance for regulatory submissions"
- "Automated validation reduces submission rejection risk"
- "Supports FDA 21 CFR Part 11 compliance requirements"

### Plan Timeline

#### High-Level Phases
Break epic into logical phases (usually quarters):

**Phase 1: Foundation (Q1 2026)**
- Basic import engine for top 2 formats (EndNote XML, RIS)
- Simple deduplication by DOI
- Manual conflict resolution UI
- **Milestone:** Beta release to 5 pilot customers

**Phase 2: Production Hardening (Q2 2026)**
- Advanced deduplication with fuzzy matching
- Automated conflict resolution with confidence scores
- Error reporting and validation
- Progress tracking for large imports
- **Milestone:** GA release to all customers

**Phase 3: Advanced Features (Q3 2026)**
- Additional formats (BibTeX, PubMed XML)
- Bulk export with templates
- Scheduled imports from external libraries
- **Milestone:** Enterprise feature parity with competitors

#### Key Milestones
Date-based checkpoints:
- "Feb 2026: Basic import working in staging (pilot testing)"
- "April 2026: GA release with top 2 formats"
- "July 2026: Full format support and export capabilities"
- "Sept 2026: Market competitive with RefWorks and Mendeley"

### Link Related Resources

#### Customer Research
- Link to customer interview transcripts
- Market research reports
- Competitive analysis documents
- Feature request Zendesk tickets (aggregate data)

**Example:**
```
- Customer Research: [link to 15 enterprise interviews from Q4 2025]
- Competitive Analysis: [link to RefWorks/Mendeley feature comparison]
- Market Research: "Forrester report: Reference Management in Pharma 2025"
```

#### Technical Context
- Architecture decision records
- Security/compliance requirements
- Performance benchmarks
- Third-party API documentation

## Step 5: Break Down into Stories (Initial)

While not required for the epic itself, provide **initial story ideas** to help with sprint planning:

### Example Story Breakdown

**Story Cluster 1: Import Engine**
- ECD-XXX: "Import EndNote XML files with basic metadata extraction"
- ECD-XXX: "Import RIS format files with field mapping"
- ECD-XXX: "Validate imported references against schema requirements"

**Story Cluster 2: Deduplication**
- ECD-XXX: "Detect duplicate references by DOI exact match"
- ECD-XXX: "Fuzzy match duplicates by title and year"
- ECD-XXX: "Manual conflict resolution UI for duplicate candidates"

**Story Cluster 3: User Experience**
- ECD-XXX: "File upload UI with format detection"
- ECD-XXX: "Progress tracking for imports >100 references"
- ECD-XXX: "Import error reporting with actionable messages"

**Note:** These are planning-level stories, not final. Actual stories will be written during sprint planning.

## Step 6: Post Draft for Approval

Format the response to the original comment:

```markdown
📋 I've analyzed this initiative and created a draft epic.

---

# Epic: [Strategic Title]

## Business Justification

### Strategic Value
[Market positioning, customer impact, business driver]

### Customer Pain Points Addressed
[Researched pain points with data]

### Competitive Advantages
[Key differentiators]

## Scope Overview

### Core Functionality Areas
[3-5 high-level capabilities]

### Integration Points
[Major system connections]

### Out of Scope
[Explicitly excluded]

## Success Criteria

### Business Impact Measurements
[Quantified metrics]

### Financial Impact
[Revenue/cost data]

## Timeline Expectations

### High-Level Phases
[Quarter-by-quarter breakdown]

### Key Milestones
[Date-based checkpoints]

## Initial Story Breakdown (Planning-Level)
[Story clusters for estimation]

---

**Next Steps:**
- Reply **'approved'** to create Jira epic ECD-XXX
- Reply **'changes: [your feedback]'** to refine
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
    source_id='ECD-123',
    request_type='epic',
    user_id='user_account_id',
    user_name='User Display Name',
    original_context='Original comment describing the initiative...',
    draft_content='Full formatted epic markdown...'
)
```

## Quality Checklist

Before posting the draft, verify:

✓ **Strategic Value is Clear**
- Connects to business goals (revenue, compliance, market position)
- Customer impact is quantified with research
- Competitive advantage is specific

✓ **Scope is Well-Defined**
- Core capabilities are clear
- Integration points identified
- Out of scope is explicit

✓ **Success Criteria are Measurable**
- Business metrics are quantified
- Financial impact has estimates
- Timelines are realistic

✓ **Timeline is Phased**
- Logical progression (foundation → production → advanced)
- Milestones tied to customer value delivery
- Quarters are realistic given team capacity

✓ **Story Breakdown is Helpful**
- Provides initial planning guidance
- Clusters logically related functionality
- Not overly prescriptive (leaves room for sprint planning)

## Common Epic Patterns in CiteMed

### Compliance/Regulatory Epics
- Focus on audit trail and validation
- Include FDA/EU MDR requirement mapping
- Success criteria tied to submission acceptance rates
- Timeline driven by regulatory deadlines

### Enterprise Feature Epics
- Emphasize scalability (bulk operations, large datasets)
- Include advanced permissions and multi-tenancy
- Success criteria tied to enterprise customer adoption
- Business case based on enterprise ARR growth

### Integration Epics
- Define API contracts and SLAs
- Include error handling and retry logic
- Success criteria tied to integration reliability
- Phases: basic connectivity → advanced features → monitoring

### AI/ML Feature Epics
- Include model training and validation phases
- Define accuracy and confidence thresholds
- Success criteria tied to user trust and adoption
- Timeline accounts for iteration on model performance

## Example: Complete Epic Generation

**User Request:** "@remington we need to create an epic for the multi-format reference import initiative we've been discussing"

**Generated Epic:**

```markdown
# Epic: Multi-Format Reference Import and Export System

## Business Justification

### Strategic Value
- **Market Positioning:** This epic establishes CiteMed as the only regulatory platform with native support for all major reference formats, removing the #1 barrier to enterprise customer adoption and achieving feature parity with academic reference managers
- **Customer Impact:** Enterprise customers managing 10,000+ references (representing 40% of our target market and $2M ARR opportunity) can migrate to CiteMed without manual data entry, reducing onboarding time from weeks to hours
- **Business Driver:** Revenue growth via enterprise segment expansion; current pipeline shows 12 enterprise opportunities blocked on import functionality, representing $360K ARR

### Customer Pain Points Addressed
- **Manual Entry Burden:** Enterprise regulatory teams spend 40-60 hours per dossier submission manually entering references (verified in 15 customer interviews Q4 2025)
- **Migration Friction:** 70% of enterprise trial users abandon platform during onboarding due to lack of EndNote import (Pendo data Oct-Dec 2025)
- **Compliance Requirements:** Regulatory auditors require provable reference provenance; manual entry lacks audit trail (Pharma compliance survey, Nov 2025)
- **Format Lock-in:** Customers currently locked into EndNote due to inability to export their 10+ years of reference data

### Competitive Advantages
- **Only regulatory platform with EndNote bidirectional sync:** RefWorks and Mendeley are academic-focused; no pharma-specific competitor offers this
- **Automated deduplication with regulatory audit trail:** Unique capability to prove which references were imported vs manually created vs duplicates merged
- **Bulk validation against regulatory requirements:** Automatically flag incomplete references that would fail FDA submission (competitor systems require manual review)

## Scope Overview

### Core Functionality Areas
1. **Multi-Format Import Engine**
   - EndNote XML (versions X7-X20)
   - RIS format (all major variants)
   - PubMed XML
   - BibTeX format
   - CSV with customizable field mapping

2. **Intelligent Deduplication**
   - DOI exact matching (primary)
   - Fuzzy title/year matching with confidence scores
   - Manual conflict resolution UI with diff view
   - Automated merge rules with audit logging

3. **Bulk Export with Templates**
   - Export to EndNote XML, RIS, CSV
   - Customizable field selection
   - Citation style formatting (AMA, APA, Vancouver, etc.)
   - Scheduled exports to external systems

4. **Import Validation and Quality**
   - Schema validation against regulatory requirements
   - Missing field detection and warnings
   - Duplicate detection before import commit
   - Error reporting with actionable fix suggestions

5. **Enterprise-Scale Performance**
   - Progress tracking for imports >1,000 references
   - Background processing with email notification
   - Retry logic for failed imports with partial rollback
   - Import history with rollback capability

### Integration Points
- **EndNote Web API:** Direct library sync (evaluate in Phase 3; may require EndNote partnership)
- **PubMed E-utilities API:** Metadata enrichment for incomplete references
- **AWS S3:** Large file storage and asynchronous processing
- **Elasticsearch:** Fuzzy duplicate detection with configurable similarity thresholds
- **Celery/Redis:** Background job processing for large imports

### Out of Scope (Future Consideration)
- **Real-time collaborative editing during import:** Complex UX, evaluate after Phase 2 adoption data
- **Mobile app import:** Separate epic; enterprise users primarily use desktop
- **Mendeley/Zotero import:** Evaluate market demand after EndNote launch; may not be worth engineering effort
- **Automated citation recommendation:** AI feature for future epic; focus on import/export first

## Success Criteria

### Business Impact Measurements
- **Customer Adoption:** 60% of new enterprise customers activate import feature within first 30 days of onboarding
- **Usage Metrics:** Average 500+ references imported per enterprise customer (proving real migration, not just testing)
- **Customer Satisfaction:** NPS score differential of +20 points for import users vs manual entry users
- **Churn Reduction:** Enterprise customer churn rate <5% (vs current 15% for manual-only workflow)

### Financial Impact
- **Revenue Impact:**
  - Close 8 of 12 blocked enterprise deals in 6 months post-GA = $240K ARR
  - Upsell import feature to existing 30 enterprise customers = $90K ARR expansion
  - **Total:** $330K ARR in Year 1
- **Cost Savings:**
  - Reduce customer success onboarding time from 8 hours to 1 hour per enterprise customer = 210 hours/year saved
  - Reduce support tickets related to manual entry errors by 50% = ~$20K/year support cost savings
- **Market Share:** Capture 15% of EndNote-using pharma companies (estimated 200 potential customers based on industry data)

### Compliance/Regulatory Benefits
- **Audit Trail:** Provable reference provenance for FDA/EMA submissions (required for 21 CFR Part 11 compliance)
- **Validation Automation:** Reduce regulatory submission rejection rate from 12% to <5% (industry benchmark: 8%)
- **Time to Submission:** Reduce reference preparation time for regulatory dossiers from 40 hours to 5 hours

## Timeline Expectations

### High-Level Phases

**Phase 1: Foundation/MVP (Q1 2026 - Jan-Mar)**
- Basic import engine for top 2 formats (EndNote XML X7-X20, RIS)
- Simple deduplication by exact DOI match
- Manual conflict resolution UI with side-by-side comparison
- File upload with format detection
- Import validation with error reporting
- **Milestone:** Beta release to 5 pilot customers by Feb 15, 2026
- **Effort Estimate:** 120 story points (~6 weeks with 2 developers)

**Phase 2: Production Hardening (Q2 2026 - Apr-Jun)**
- Advanced deduplication: fuzzy title/year matching with ML confidence scores
- Automated conflict resolution with configurable merge rules
- Progress tracking for large imports (>1,000 references)
- Background processing with email notifications
- Import history with rollback capability
- Performance optimization for 10,000+ reference imports
- **Milestone:** GA release to all customers by May 1, 2026
- **Effort Estimate:** 100 story points (~5 weeks)

**Phase 3: Advanced Features (Q3 2026 - Jul-Sep)**
- Additional import formats (PubMed XML, BibTeX)
- Bulk export with customizable templates
- Citation style formatting (AMA, APA, Vancouver)
- Scheduled imports from external libraries (if EndNote API partnership secured)
- CSV import with custom field mapping
- **Milestone:** Enterprise feature parity with academic reference managers by Aug 1, 2026
- **Effort Estimate:** 80 story points (~4 weeks)

### Key Milestones
- **Feb 15, 2026:** Beta release with EndNote XML and RIS import to 5 pilot customers (enterprise tier)
- **Mar 1, 2026:** Pilot feedback incorporated; deduplication accuracy >95% on pilot data
- **May 1, 2026:** GA release with core import/export to all customers
- **Jun 1, 2026:** First 3 enterprise deals closed using import feature as key differentiator
- **Aug 1, 2026:** Full multi-format support; competitive feature parity achieved
- **Sep 30, 2026:** Post-launch review: adoption metrics, revenue impact, customer feedback for Phase 4 planning

## Related Resources

### Customer Research
- **Enterprise Interview Synthesis (Q4 2025):** [Link to 15 pharma customer interviews] - Key finding: EndNote import is #1 requested feature
- **Competitive Analysis:** [RefWorks vs Mendeley vs Zotero feature comparison, Dec 2025]
- **Market Research:** Forrester "Reference Management in Life Sciences 2025" - Market size: $40M, growing 12% YoY
- **Feature Requests:** [Zendesk aggregation report] - 47 tickets requesting EndNote import over past 12 months

### Technical Context
- **Architecture Decision Record:** [ADR-023: Asynchronous Import Processing with Celery]
- **Security Requirements:** [SEC-REQ-012: File Upload Validation and Sandboxing]
- **Performance Benchmarks:** [PERF-TEST-2025-12: Import performance targets for 1K, 10K, 50K references]
- **Third-Party APIs:**
  - EndNote XML Schema Documentation v20
  - PubMed E-utilities API docs
  - AWS S3 upload best practices

---

**Epic Owner:** Product Manager (Ethan)
**Technical Lead:** TBD (assign during Phase 1 planning)
**Stakeholders:** Customer Success (enterprise onboarding), Sales (enterprise deals), Compliance (regulatory requirements)
**Created:** 2025-11-13
**Last Updated:** 2025-11-13
**Target Start:** Q1 2026 (Sprint 2026-01)

## Initial Story Breakdown (Planning-Level)

### Story Cluster 1: Import Engine Foundation (Phase 1)
- **ECD-XXX:** Import EndNote XML files with metadata extraction (all standard fields)
- **ECD-XXX:** Import RIS format files with field mapping to CiteMed schema
- **ECD-XXX:** File upload UI with drag-and-drop and format auto-detection
- **ECD-XXX:** Import validation: detect required missing fields and show warnings

### Story Cluster 2: Deduplication (Phase 1)
- **ECD-XXX:** Exact DOI match deduplication during import preview
- **ECD-XXX:** Manual conflict resolution UI with side-by-side diff view
- **ECD-XXX:** Merge selected duplicate references with audit log entry

### Story Cluster 3: User Experience (Phase 1)
- **ECD-XXX:** Import preview screen showing: new references, duplicates, errors
- **ECD-XXX:** Bulk import action with progress indicator (for <1,000 refs)
- **ECD-XXX:** Import success/error reporting with actionable next steps

### Story Cluster 4: Advanced Deduplication (Phase 2)
- **ECD-XXX:** Fuzzy title+year matching with ML confidence scores
- **ECD-XXX:** Automated conflict resolution with configurable merge rules
- **ECD-XXX:** Deduplication accuracy testing and threshold tuning

### Story Cluster 5: Performance & Scale (Phase 2)
- **ECD-XXX:** Background processing for imports >1,000 references (Celery workers)
- **ECD-XXX:** Real-time progress tracking with WebSocket updates
- **ECD-XXX:** Email notification when background import completes
- **ECD-XXX:** Import history page with status tracking and rollback option

### Story Cluster 6: Export (Phase 3)
- **ECD-XXX:** Export references to EndNote XML format with field mapping
- **ECD-XXX:** Export to RIS format with customizable field selection
- **ECD-XXX:** Export to CSV with custom column configuration
- **ECD-XXX:** Bulk export UI with format selection and preview

### Story Cluster 7: Additional Formats (Phase 3)
- **ECD-XXX:** Import PubMed XML format with NLM field mapping
- **ECD-XXX:** Import BibTeX format with LaTeX field parsing
- **ECD-XXX:** CSV import with custom field mapping wizard

**Note:** These are planning-level stories. Actual stories will be refined during sprint planning with acceptance criteria, technical approach, and effort estimates.
```

This epic is comprehensive, strategic, and provides clear business justification with measurable success criteria.

---

**Remember:** Epics are strategic documents. They should inspire confidence in the business value while providing enough structure for technical planning.
