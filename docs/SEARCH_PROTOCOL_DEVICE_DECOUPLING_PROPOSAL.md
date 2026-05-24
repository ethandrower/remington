# Search Protocol — Device Field Decoupling - Proposal

**Date:** 2026-05-11
**Author:** PM Agent (Remington) + Ethan Drower
**Status:** Proposal / Discovery
**Jira:** TBD (MDP idea to be filed)

---

## Origin

Ethan flagged on 2026-05-11 that in the **Search Protocol** tab, the *Device Description*, *Intended Use*, and *Indication of Use* fields are not user-editable per-project. They display values read from the central admin-panel **Device** definition. Two problems with this:

1. **Functional gap:** A project's protocol may need device wording tailored to the specific review (regulatory framing, scope of indication) without altering the central definition.
2. **Data-integrity risk:** When an admin edits the central Device, **all existing projects' protocols change retroactively**. Past reviews lose the wording they were authored under — a serious audit-trail problem for regulatory work.

## Current State

**Model layer is already correct.** `SearchProtocol` (in `citemed_web/lit_reviews/models/literature_reviews.py`) already has local fields:

```python
device_description = models.TextField(null=True, blank=True)
intended_use      = models.TextField(null=True, blank=True)
indication_of_use = models.TextField(null=True, blank=True)
devices = models.ManyToManyField("lit_reviews.Device", related_name="search_protocols", ...)
```

`citemed_web/lit_reviews/report_builder/protocol_context_builder.py` reads from `protocol.device_description` etc. (snapshot-correct).

**So the bug isn't in the schema.** It's in one of three places:

- **(A) Frontend Vue** reads from the related `Device` record and overrides the protocol's local fields. Likely if the field never appears editable in the Search Protocol UI.
- **(B) Serializer** substitutes `device.description` for `protocol.device_description` in API responses. Check `lit_reviews/api/home/serializers.py` and `lit_reviews/api/search_terms/serializers.py`.
- **(C) Form/create flow** never populates `protocol.device_description` on project creation, so it stays NULL and the UI silently falls back to the related `Device`'s text.

**Verification needed before sizing the fix.** The proposal below assumes (C) plus partial (A) — UI doesn't expose the field editably, and protocol fields are blank because no one populates them at creation.

## User Requirement

> "In the search protocol tab I should be able to edit the device description and related fields. Right now it only pulls straight from the admin panel device definition. And there is a bug and big RISK because when admin changes device info — it affects all the existing projects' protocols automatically. Instead we should copy one time from admin device config → project and then allow user to edit the copy of it only."

— Ethan Drower, 2026-05-11

## Proposed Solution — MVP

Snapshot device fields onto the project's `SearchProtocol` at protocol creation, expose them as editable in the UI, never re-read from the live Device record for display.

**Concretely:**

1. **Backfill at protocol creation:** When a `SearchProtocol` is created (or first associated with a Device), populate `device_description`, `intended_use`, `indication_of_use` from the related Device's corresponding fields. One-time copy.
2. **Surface editable fields in the Search Protocol UI:** Add or unhide form inputs for the three fields. Save edits to the `SearchProtocol`, not the `Device`.
3. **Stop reading from `Device.*` in the protocol API/serializer.** All reads come from `protocol.*`. The `devices` M2M stays as a relational link (which Device this protocol is *about*), but textual fields are now protocol-scoped.
4. **Migration for existing protocols:** Data migration that, for every existing `SearchProtocol` with blank text fields and at least one linked `Device`, copies the first linked Device's fields into the protocol. One-shot; logs which protocols were backfilled.

## Out of Scope (deferred)

- **Versioning / history of edits** to the protocol device fields (could be a follow-up: per-field change log).
- **Admin warning at edit time** ("you're editing a Device used by N existing projects — none will change") — UX polish for the admin side.
- **Decoupling other admin-defined config** that may have the same flaw (extraction fields, indication lists, etc.) — file separately if confirmed.
- **Comparator devices / SoTA fields** snapshot — the same decoupling pattern may apply but is a separate scope.

## Technical Approach

- **Backend (Django):**
  - Add a `post_save` signal on `SearchProtocol` (or override `save()`) that, on creation only, populates the three text fields from the first linked Device if blank.
  - Audit `lit_reviews/api/home/serializers.py` + adjacent serializers to ensure protocol-scoped fields are returned (not Device fields). Likely just confirming current state — server-side may already be correct.
  - Data migration: `python manage.py backfill_protocol_device_fields` (idempotent).
- **Frontend (Vue):**
  - In the Search Protocol tab, replace any read-only `device.description` binding with an editable input bound to `protocol.device_description`. Same for the other two fields.
  - On the project creation flow ("Copy device fields from selected Device" preview), keep the auto-fill behavior but make the values editable before save.
- **Data integrity:** All historical protocols' fields will be backfilled by the migration. After ship, no admin edit of the Device touches any existing protocol.

## Acceptance Criteria

1. Editing `Device.description` in the admin panel does **not** change the displayed device description on any existing project's Search Protocol.
2. On any Search Protocol with a linked Device, the three fields (`device_description`, `intended_use`, `indication_of_use`) are visible and editable.
3. Edits persist to the `SearchProtocol` and survive page reload.
4. Newly created Search Protocols pre-fill the three fields from the linked Device once at creation, then never re-pull.
5. Data migration completes successfully against staging and prod data: every existing SearchProtocol with a linked Device has the three fields populated (either with prior local edits or backfilled from Device).
6. Regression: report generation (`protocol_context_builder.py` and downstream) shows the protocol-scoped values, not the live Device values, in generated outputs.

## Estimate

**Total (rough): 4–6 hours**

- 1h — Diagnose where the UI/serializer currently reads from (rule out scenarios A vs B vs C).
- 1h — Backend: signal/save override + data migration.
- 1h — Serializer audit + tests.
- 1–2h — Frontend: editable fields + Search Protocol form wiring.
- 1h — End-to-end test against staging, regression check on report generation.

**Critical path:** the diagnosis step. If the bug is in scenario (A) (frontend hardcoded to Device), backend changes may be unneeded and total drops to ~3h. If it's (B) + (C) combined, full plan applies.

## Dependencies

- Read access to `citemed_web/lit_reviews/` (already have it).
- Knowledge of which dev currently owns the Search Protocol UI surface (worth tagging during refinement).
- Coordination with anyone working **ECD-1881** (Vigilance Project device-selection bug) and **ECD-1707** (Vigilance project creation issues) since both touch device + project flows — risk of overlapping serializer edits.

## Open Questions

1. **Which scenario (A/B/C) is the actual bug?** Confirmation diagnoses whether this is backend + frontend or frontend-only.
2. **Do we also need to snapshot the M2M `devices` relation?** I.e., if admin deletes a Device, should existing protocols retain it as a reference? Or only the textual fields snapshot? Recommend: keep M2M live (so the project still knows "this protocol is about Device X"), only snapshot the text.
3. **Audit logging:** Should edits to these fields be recorded for regulatory traceability? May already be handled by an existing audit-log mechanism.
4. **Same fix scope for `sota_description`, `sota_product_name`, `comparator_devices`?** They appear in `protocol_context_builder.py` alongside the affected fields and may have the same issue. Worth investigating in parallel but filing separately if confirmed.

## Why This Matters

**Regulatory & audit integrity.** Search Protocols are part of the formal record for medical-device literature reviews (CER / PMS / Vigilance). The current behavior means a single admin edit can silently rewrite the documentation underpinning closed reviews — a finding-grade compliance risk for clients in regulated markets. Decoupling fixes both the data-integrity exposure and removes a real workflow blocker (users currently can't tailor protocol wording per project).

**Adjacent to Epic ECD-1834 (Admin Configuration Experience)** which scopes the admin-config UX. This proposal is the *inverse* direction — protecting projects from admin changes — and should be linked as "relates to" for cross-team awareness.
