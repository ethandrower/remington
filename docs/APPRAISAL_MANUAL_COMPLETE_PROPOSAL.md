# Manual "Mark as Complete" for Clinical Appraisals — Proposal

**Date:** 2026-05-21
**Author:** PM Agent + Ethan Drower
**Status:** Proposal — ready to file

---

## Origin

Ethan asked on 2026-05-21 whether the false-incomplete-status bug from the legacy version was fixed. It is not — `ClinicalLiteratureAppraisal.status` (`citemed_web/lit_reviews/models/appraisals.py:67-156`) derives completion purely from per-field non-emptiness via `check_extraction_section_completion()` (`citemed_web/lit_reviews/helpers/articles.py:526-545`). A reviewer who finished reviewing an article but intentionally left optional fields blank (e.g. because the article is SoTA and only contributes background context) sees the appraisal flagged "Incomplete Extraction Fields" on the list page.

Ethan's preferred shape: **let reviewers manually mark an appraisal as complete; the manual flag overrides the auto-calculated field-completeness status.** Explicitly rejected: hard-coding rules like "if SoTA then fields 1,3,5 apply."

## Current State

- **Model:** `ClinicalLiteratureAppraisal` has no reviewer-completion flag — only the derived `app_status` string. (`citemed_web/lit_reviews/models/appraisals.py:5-44`)
- **Status engine:** `status` property cascades through ordered checks; the only "Complete" path requires every extraction field to be non-empty. (`citemed_web/lit_reviews/models/appraisals.py:67-156`)
- **Save-and-next flow already has the right surface:** clicking "Complete & Next" while `pendingFields.length > 0` opens `IncompleteFieldsModal.vue` with two options:
  - *Review* — close the modal, stay on this appraisal
  - *Save & Next* — saves as draft, moves on, but the appraisal **stays in "Incomplete" status** (this is the gap)
- **Stats bar already understands the distinction:** `helpers/articles.py:422-424` exposes `UncompleteExceptExtractions` as a roll-up metric (Total − Complete − Incomplete-Extraction-Fields). Someone already recognized that field-incompleteness ≠ review-incompleteness; the per-row badge just doesn't reflect it.
- **Related Jira (closed):** ECD-845 (report generation didn't gate on completeness; fixed using the same broken signal — so this fix should be reviewed against report-gating too).
- **Adjacent in Discovery (NOT duplicates):**
  - **MDP-216** — Optional SoTA-vs-Device flow. Proposes an AI classifier + conditional extraction so SoTA articles only get the fields that apply. Rule-based / template-driven.
  - **MDP-225** — Evidence-type-aware platform. Same family, larger framing — `ExtractionTemplate` grid keyed on (Article-Type × Article-Role) decides which fields are active per template.

Both adjacent ideas try to be *smart enough* to know applicability. This proposal is the **complementary escape hatch** — works today, requires no AI, and remains useful after MDP-216/225 ship for the edge cases templates miss.

## User Requirement

> *"users should be able to 'mark the article as complete' when they are done reviewing it. and this manual completion could override any auto-calculated status based on the fields completed. i want to avoid hard coding in 'rules' like 'if it's a sota article, then only fields 1,3,5 apply'"*

> *"my guess is the modal that pops up when they save and next an article but don't have all the fields filled out"*

## Proposed Solution — MVP

A **reviewer-set boolean** that overrides the derived status, surfaced through the existing `IncompleteFieldsModal` as a third action.

**Backend:**
1. Add three fields to `ClinicalLiteratureAppraisal`:
   - `marked_complete_by_reviewer: BooleanField(default=False)`
   - `marked_complete_by: ForeignKey(User, null=True, related_name="+")`
   - `marked_complete_at: DateTimeField(null=True)`
2. In the `status` property, **short-circuit to `"Complete"` if `marked_complete_by_reviewer` is True**, regardless of field state. (Insert at top of `appraisals.py:67-156` after the `if self.pk` check.)
3. Status counter in `helpers/articles.py:get_clinical_appraisal_status_report` already routes any `"Complete"` string into the right bucket — no changes needed there once the property short-circuits.
4. New API endpoint or `PATCH` on the existing appraisal endpoint accepting `{marked_complete_by_reviewer: bool}`. Sets `marked_complete_at = now()` and `marked_complete_by = request.user` on transition false→true; clears both on true→false.

**Frontend — UX surface (`IncompleteFieldsModal.vue`):**
The current modal has two buttons: *Review* and *Save & Next*. Add a **third primary action: "Mark as Reviewed & Next"**, which:
1. Calls the new endpoint to set `marked_complete_by_reviewer = True`
2. Saves the appraisal as draft (same as current Save & Next does)
3. Advances to the next appraisal

Recommended button order in the modal: `[Review] [Save & Next (draft)] [Mark as Reviewed & Next]`. Refine copy with Design — current modal title "Incomplete Fields Detected" reads accusatory and may need softening once a third action exists.

**Frontend — list page (`clinical-appraisals-list/`):**
- `AppraisalStatusBadge.vue` requires no changes — it just renders whatever string the backend returns. When `status` short-circuits to `"Complete"`, the badge updates automatically.
- Optional: small "manually marked" indicator (e.g., subtle pencil icon next to the Complete badge) so QC can distinguish manual-Complete from field-driven-Complete. Defer to Design.

**Frontend — appraisal page direct action:**
Optional second surface — a "Mark as Reviewed" toggle in `AppraisalActions.vue` so reviewers don't have to trigger Complete & Next to flip the flag. Keep MVP scoped to the modal first; this can land as a fast-follow once the field is in place.

## Out of Scope (deferred)

- **Reverting a manually-completed appraisal** — MVP supports it via the same toggle (set flag false), but the UX for "I marked this complete by mistake" needs design. Punt the bulk-action flow to a follow-up.
- **Approver / second-reviewer sign-off chain.** Single-reviewer flag only.
- **Different visual treatment** for manual-Complete vs field-driven-Complete in the list-page badge. Identical badge in MVP; optional indicator is a fast-follow.
- **Auto-mark-complete when the reviewer fills every field.** Behavior stays: field-completeness still routes through the existing status engine. Manual flag only matters when fields *aren't* all filled.
- **Required vs optional fields per ExtractionField template** (Option 2 from my earlier writeup). That overlaps MDP-216/MDP-225's solution space — defer.
- **Report-builder integration.** ECD-845 closed the gate that uses the broken signal; this fix needs a follow-up to verify report-gating now respects `marked_complete_by_reviewer`. File as a small linked story, not part of MVP.
- **Confirmation modal before mark-complete-with-many-blank-fields.** Could nag if 50%+ blank, but adds friction and contradicts the user's "avoid rules" preference. Skip.

## Technical Approach

**Migration:**
```python
# lit_reviews/migrations/03XX_appraisal_manual_complete.py
operations = [
    migrations.AddField('ClinicalLiteratureAppraisal', 'marked_complete_by_reviewer',
                        models.BooleanField(default=False)),
    migrations.AddField('ClinicalLiteratureAppraisal', 'marked_complete_by',
                        models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                          null=True, blank=True, related_name='+')),
    migrations.AddField('ClinicalLiteratureAppraisal', 'marked_complete_at',
                        models.DateTimeField(null=True, blank=True)),
]
```

**Model:**
```python
# appraisals.py:67-156 -- short-circuit at top of the status property
@property
def status(self):
    if self.pk and self.marked_complete_by_reviewer:
        return "Complete"
    # ... existing logic ...
```

**API:** Extend the existing appraisal `PATCH` endpoint in `lit_reviews/api/clinical_appraisals/views.py` to accept the new field. On transition False→True set `marked_complete_at=timezone.now()` and `marked_complete_by=request.user`; on True→False clear both. Serializer in `lit_reviews/api/clinical_appraisals/serializers.py`.

**Frontend:**
- Add third action button + handler in `ClinicalAppraisalApp.vue` next to existing `handleIncompleteFieldsSaveAndNext` (around line 384).
- Update `IncompleteFieldsModal.vue` to emit a new `mark-complete-and-next` event in addition to current `save-and-next` and `close`.
- Store action calls the new endpoint, then proceeds with normal save+navigate.

**Audit:** Use existing audit-log machinery (if any) on the appraisal model; otherwise the `marked_complete_by` + `marked_complete_at` fields are sufficient breadcrumbs for QC.

## Acceptance Criteria

- A reviewer on `ClinicalAppraisalApp.vue` clicks "Complete & Next" with some fields blank, sees the modal, clicks "Mark as Reviewed & Next."
- The appraisal's `marked_complete_by_reviewer` becomes True; `marked_complete_by` is the current user; `marked_complete_at` is set.
- Returning to the appraisals list page (`ClinicalAppraisalsListApp.vue`), the row shows the "Complete" badge.
- `get_clinical_appraisal_status_report` counts the appraisal in `Complete` and the appropriate `Complete SoTa Reviews` / `Complete Device Reviews` bucket.
- Toggling the flag back to False (via the same modal action when reopened, or via an Actions menu — TBD with Design) restores the prior derived status and clears `marked_complete_at` / `marked_complete_by`.
- An appraisal with all fields filled in (where the derived status was already "Complete") behaves identically whether `marked_complete_by_reviewer` is True or False.

## Estimate

- BE: model + migration + status short-circuit + serializer + endpoint = **~3h**
- FE: third modal action + handler + API call wiring = **~3h**
- Tests (backend status property, serializer, FE handler unit test) = **~2h**
- QA + edge cases (toggle back-and-forth, transition cleanup, list-page refresh) = **~1h**

**Total: ~9h.** Fits in one focused work session; well within MVP discipline.

**Critical path:** model + status-property short-circuit. Everything else depends on those two.

## Dependencies

- None blocking. Database migration is additive; existing data unchanged (all rows start with `marked_complete_by_reviewer=False`, so behavior is identical until reviewers opt-in).
- **Coordinate with Design** on third-button copy and whether the modal title needs softening — both small but worth a quick alignment.

## Open Questions

- **Q1: Reversal UX.** Where does "I marked this complete by mistake — unmark it" live? Options: (a) modal again (only fires if `pendingFields > 0`), (b) toggle in `AppraisalActions.vue`, (c) a small chip-with-X next to the Complete badge on the appraisal page. MVP: only via modal; fast-follow (b) or (c).
- **Q2: Should the "Don't Show Again" preference apply per-user only, or could the project owner force the modal back on?** Current implementation is per-browser localStorage — fine for MVP, may need productizing later.
- **Q3: Visual distinction in the list-page badge** between "field-derived Complete" and "manually-marked Complete." Defer to Design — strong opinion not held.
- **Q4: Report-gating downstream impact.** ECD-845 closed reports being generated against incomplete appraisals. Verify the gate now uses the same `status` property (and therefore respects the override) vs. duplicating the field-completeness check elsewhere. File a small linked verification ticket as follow-up.

## Why This Matters

Two compounding effects:

1. **It removes a daily papercut.** Today reviewers can finish reviewing an article they intentionally left some fields blank on (because the field doesn't apply) and the system flags them as having unfinished work. The badge on the list page lies. The stats bar lies. That erodes trust in the system *and* makes the dashboards useless for project progress tracking.

2. **It complements, not competes with, the bigger initiatives.** MDP-216 and MDP-225 propose template-driven applicability — eventually the system gets *smart* about which fields apply per article type. That's the right long-term answer, but it's months out and rule-based systems will always miss edge cases. Shipping a manual override now:
   - Fixes the immediate UX problem
   - Doesn't lock in any hard-coded applicability rules (the user's explicit constraint)
   - Stays useful after templates ship — the universal escape hatch for cases templates don't cover

This is a small, surgical fix to a misaligned signal. ~9h. The hard part is already done — `IncompleteFieldsModal.vue` is the right surface, and `helpers/articles.py:422` proves someone already understood the distinction.
