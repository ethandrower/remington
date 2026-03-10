# QA Guidelines: PR Evaluation & Test Case Design
**Source:** Confluence ENG-02 - QA Guidelines
**Last Updated:** 2026-02-12

## Purpose
This document defines:
- How and when QA is involved in ticket definition, to ensure stories are testable before development starts
- How QA evaluates a Pull Request (PR) in Bitbucket, in the context of Jira stories and the SDLC
- How QA designs and documents good test cases for new features, changes, and bug fixes

**Parent Document:** ENG-02 - SDLC

---

## 1. Scope & Responsibilities

These guidelines apply to:
- All Jira tickets that move to QA status as part of Phase 3 – Testing & QA
- All corresponding Bitbucket PRs created from those tickets
- All QA engineers assigned in the QA Assignee field on the Jira ticket

**Roles:**
- **Primary owner:** QA team
- **Supporting roles:** Developers, Tech Lead, Product Manager (PM), CTO (for escalations)

---

## 2. QA Involvement in Ticket Definition

QA shall be involved **before development starts**, as part of ticket definition/refinement. For each ticket that will go through QA:

**QA is expected to:**
- Review the Acceptance Criteria (AC) for clarity and testability
- Flag missing edge cases, negative scenarios, and data/permission considerations
- Identify any special test data or environments needed

**A ticket is "ready for development" only if:**
- ACs are clear and testable (QA agrees they can be validated)
- Any known test constraints (e.g., "requires external API sandbox") are documented
- The ticket is linked to relevant epic/design/requirements so QA can understand context

**QA participation can happen via:**
- Refinement/grooming meetings, or
- Async review of new tickets in Jira, with comments for PM/dev where ACs are unclear

⚠️ **Important:** If QA has not reviewed the ACs, the ticket may still proceed, but QA can block release later if behavior is ambiguous or untestable. Earlier QA input reduces rework and "Change Requested" cycles.

---

## 3. How to Evaluate a PR (QA Workflow)

When a PR is created, the associated Jira story automatically enters QA. The responsible QA follows these steps:

### 3.1 Inputs QA Must Have Before Testing

For each ticket under QA:

**A Jira story with:**
- Clear Acceptance Criteria (AC) defined
- Links to related items (epics, bugs, design docs, linked work items per SDLC)
- Release Version, priority, start/due dates, and QA Assignee set

**A Bitbucket PR that includes:**
- Reference to the Jira ticket in the title and/or description
- A staging link or instructions on how to access the feature
- Any known limitations or special setup called out by the developer
- Test data or user accounts needed to exercise the functionality

⚠️ **If any of the above are missing:** QA should comment on the Jira ticket and/or PR and pause testing until the information is provided.

### 3.2 PR Evaluation Checklist (What QA Looks For)

When opening the PR, QA should verify at minimum:

#### ✅ Jira Linkage & Scope
- PR is clearly linked to one primary Jira ticket
- Description matches the scope of the Jira story (no surprise scope creep)
- If the PR fixes bugs that belong to other tickets, those are:
  - Either explicitly documented in PR description, or
  - Logged as separate Jira bugs, linked with "caused by" or another appropriate relationship

#### ✅ Clarity of Changes
- Summary of what changed is understandable to a non-author developer
- Screenshots or short demo video are included when UX/UI is impacted
- Any migration, data, or configuration changes are documented

#### ✅ Risk Assessment
- Identify impact areas for targeted regression:
  - Shared components used elsewhere
  - Critical flows (login, permissions, payments, core workflows, etc.)
- Note any dependencies (e.g., feature flags, backend changes, 3rd-party services)

#### ✅ Basic Code & Quality Signals
(Light QA review, not full dev review)
- PR is not unreasonably large without good reason (huge PRs = higher risk)
- Tests (unit/integration) referenced by dev are present and passing
- No obvious debug code/console logs/TODOs left in

**If any major concerns arise:**
- Comment directly on the PR
- Optionally transition Jira to "Change Requested" with a short summary

### 3.3 Executing Testing Against the PR

Once the PR passes the high-level evaluation, QA executes testing in the appropriate environment (usually staging-dev):

#### ✅ Validate Acceptance Criteria
- For each AC in the Jira ticket:
  - Create at least one positive test case
  - Create negative/edge cases where relevant
  - Ensure the feature behaves as described (happy path)

#### ✅ Functional Testing
- Verify data validation, state transitions, and expected side effects
- Confirm relevant permissions and roles behave correctly (who can see/do what)

#### ✅ Targeted Regression
- Based on risk assessment, identify:
  - Neighboring screens, impacted components, or flows to test briefly
  - Run smoke checks on those—especially for shared components

#### ✅ Cross-Browser/Device (Light)
At minimum:
- Chrome (desktop)
- Safari (desktop, if applicable to user base)
- Focus on visual layout and critical functionality only

#### ✅ Non-Functional Checks (Light)
- Page loads within a reasonable time, no obvious performance degradation
- No new security issues:
  - Access control violations (unauthorized actions)
  - Sensitive data visible where it shouldn't be

### 3.4 Documenting Test Cases in the PR (Mandatory)

⚠️ **MANDATORY:** Per SDLC expectations, QA must comment on the PR with the specific test cases they executed OR created for the feature.

**Use a consistent format, for example:**

```
QA Test Cases – [Name, Date]
Environment: QA
Browser(s): Chrome 122, Safari 17

AC: User can create a new Literature Review project

Steps:
1. Log in as qa_user@example.com
2. Navigate to Dashboard → "New Project"
3. Select "Literature Review" template
4. Fill required fields and click "Create"
Expected: Project is created; redirected to project overview
Result: PASS

Negative: Missing required field blocks project creation
Steps: …
Expected: …
Result: PASS

Regression: Existing project loading unaffected
Steps: …
Result: PASS

Issues found:
[#1] Minor UI misalignment on Safari (does not block release) – logged in Jira as SUP-123, linked as "caused by" this story.
```

**This PR comment is the source of truth for what was tested for that change.**

### 3.5 Handling Bugs Found During PR Testing

Follow the bug workflow aligned with the SDLC:

#### A. Bugs that block the current story (critical or major):
- Add a single PR comment listing all blocking issues in a numbered list:
  - Issue 1 – steps, expected vs actual, severity
  - Issue 2 – …
- Transition Jira ticket to "Change Requested"
- These bugs do **not** need separate Jira bug tickets unless:
  - They are large/complex and require separate tracking, or
  - They will not be fixed within this same story

#### B. Non-blocking or out-of-scope bugs:
For bugs that:
- Do not break the functionality under test, and
- Are outside of the story's acceptance criteria, or
- Are discovered after the PR is merged

**Create a single Jira bug ticket** (or small set if clearly separate), including:
- Clear steps to reproduce
- Expected vs actual
- Screenshots/videos, environment + browser info
- Linked to the original story/epic per "Linked Work Items" rules, using an appropriate link type (e.g., "caused by")
- Assign to PM/Tech Lead (backlog) for prioritization in future sprints

### 3.6 Approving or Rejecting the PR

**If all critical issues are resolved and testing passes:**
- In Jira: Move ticket from **QA → Pending Approval**
- In Bitbucket: **Approve the PR** (mandatory if QA approves the Jira ticket and PR is still open)
- Keep QA test case comment intact for traceability

**If issues remain:**
- Keep Jira ticket in "Change Requested"
- Create a new comment on 'issues found' in PR, clearly marking:
  - Which issues are fixed and retested
  - Which issues are still open
- Only once all blocking issues are resolved and retested, repeat the approval flow

### 3.7 What QA and Developers Should Avoid

**QA should avoid:**
- Creating multiple Jira bugs for the same parent task unless there are multiple major-impact bugs that truly need separate tracking
- Multiple QA engineers testing the same ticket unless explicitly requested (e.g., for cross-checking high-risk items)

**Developers should avoid:**
- Continuing to work on new tasks while delaying fixes for a ticket in "Change Requested" state
- Tasks with "Change Requested" status are a priority to address

---

## 4. How to Write Good Test Cases

### 4.1 Principles of Good Test Cases

Good test cases are:
- **Clear** – anyone on the team can follow them
- **Traceable** – mapped to specific ACs or requirements
- **Repeatable** – produce consistent results
- **Focused** – each case validates one meaningful behavior
- **Risk-aware** – cover both happy path and likely failure scenarios

### 4.2 Minimum Test Coverage Per Story

For each Jira story, QA should aim for:
- At least one test case per AC (happy path)
- Negative cases for:
  - Missing or invalid input
  - Unauthorized access or role-based restrictions
- Regression checks for the most impacted existing behavior
- Cross-browser checks for UI changes (Chrome + Safari desktop)

### 4.3 Standard Test Case Template

```
ID: TC-<StoryKey>-<number> (e.g., TC-ECD-123-01)

Related Jira Issue(s): ECD-123, ECD-456 (links)

Title: Short, descriptive (e.g., "Create new Literature Review project – happy path")

Preconditions:
- User logged in as …
- Test data exists …

Steps:
1. …
2. …

Expected Result:
- Clear and objective statement of outcome

Actual Result: (filled during execution)
- PASS / FAIL, with short note

Environment:
- Staging / Pre-Prod, browser versions, device, etc.

Type:
- Functional / Regression / Negative / Performance (light) / Security (light)
```

**Storage Options:**
You don't need a formal test case management system to use this; the same structure can live:
- As a table in Confluence, or
- Within the QA comment on the PR, or
- As sub-tasks or checklists in Jira under the main story

### 4.4 Examples

#### Example 1 – Functional, Happy Path
```
ID: TC-ECD-231-01
Title: User can add a reference to an existing Literature Review project
Related Issue: ECD-231

Preconditions:
- User qa_user logged in
- Existing project "Onboarding Test Project" exists

Steps:
1. Navigate to the project
2. Click "Add Reference"
3. Paste valid PubMed ID
4. Click "Import"

Expected Result:
- Reference appears in the reference list with status "Imported"
- No errors shown

Type: Functional
```

#### Example 2 – Negative
```
ID: TC-ECD-231-02
Title: User cannot add a reference with invalid PubMed ID

Steps / Expected:
- Use invalid ID → App shows validation error, does not add reference
```

### 4.5 When to Add / Update Test Cases

Add or update test cases:
- When new stories are created (initial design)
- When ACs change during refinement
- When regression issues are found (add new cases to prevent recurrence)

**Ensure at least the final executed cases are documented in the PR QA comment for traceability.**

---

## Test Quality Assessment Criteria (for PM Agent)

Based on the above SOP, here are the automated assessment criteria:

### ✅ PASS (Score: 8-10)
- [ ] QA test case comment exists on PR (Section 3.4)
- [ ] At least one test case per AC (Section 4.2)
- [ ] Negative/edge cases documented (Section 4.2)
- [ ] Cross-browser testing evidence (Section 3.3)
- [ ] Regression checks performed (Section 3.3)
- [ ] Test case format follows template (Section 4.3)
- [ ] Environment and browser versions documented
- [ ] All test results are PASS or non-blocking issues documented

### ⚠️ NEEDS WORK (Score: 5-7)
- [ ] Test cases exist but incomplete coverage
- [ ] Missing negative cases
- [ ] No cross-browser evidence
- [ ] Vague test steps or expected results
- [ ] Some blocking issues not resolved

### ❌ FAIL (Score: 0-4)
- [ ] No QA test case comment on PR
- [ ] No test cases documented anywhere
- [ ] Missing critical AC validation
- [ ] Blocking issues unresolved
- [ ] Ticket in "Change Requested" for >48 hours without update

### 🔍 RED FLAGS (Auto-escalate)
- [ ] PR merged without QA approval
- [ ] Ticket moved to "Pending Approval" without test case documentation
- [ ] Multiple blocking bugs not addressed
- [ ] Test cases reference wrong ticket or outdated ACs
