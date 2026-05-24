# Artifact Editor — Concurrent Editing UX - Proposal

**Date:** 2026-05-13
**Author:** PM Agent + Ethan Drower
**Status:** Proposal / Design Phase

---

## Origin

Ethan asked on 2026-05-13 whether any tickets exist for multi-user collaboration on the Artifact editor. None found. He stated a preference: **NOT** Google-Docs-style live cursors / live collab ("it's messy") — instead a UX where the user who's editing can **lock a specific section** while they work.

## Current State

- Artifact editor ships today as effectively single-user. There is no presence indicator, no locking, no real-time sync.
- Related in-flight work:
  - **ECD-1286** (Epic, In Progress) — Artifact Home UX
  - **ECD-1292** (Story, Ready for Design) — Artifact Detail Screen. Covers save UX, version control, comments, @mentions, reviewer workflow — all *asynchronous* collaboration. Does not address simultaneous editing.
  - **ECD-1817** (Bug, Highest) — Editor changes silently lost on save. Single-user data-loss defect, but the same failure mode (last-write-wins clobber) is amplified by concurrent edits and is adjacent to this work.
  - **ECD-1815** — Clio (Copilot) Artifact Editor Integration. Out of scope here (AI, not human-vs-human).
- No `artifact-editor` label exists; no code in `src/` mentions presence/locking/CRDT/Yjs.

## User Requirement

> "Real-time collaboration for users. We are NOT sure if we even want live collaboration because it's messy. We will want some UX where the user that's editing can 'lock' a specific section — vs. Google Docs style live cursor."

Translated:
- Multiple users need to be able to *coexist* in the same artifact safely.
- Conflict-avoidance model is **soft section-level locking** (preferred hypothesis), NOT operational-transform/CRDT live editing.
- "Real-time" here means *real-time presence + lock state*, not real-time character-by-character sync.

## Proposed Solution — MVP

A **section-level soft-lock** model with presence indicators. Sections are the unit of exclusivity; the rest of the document is read-only to other users while a section is locked.

**MVP behaviour:**
1. When User A starts editing a section, the section is "locked" to User A.
2. Other users see the section grayed/read-only with a banner: *"Jane is editing this section — last activity 12s ago"*.
3. Lock auto-releases on:
   - User A explicitly saves and exits the section
   - 2 min of editor inactivity (heartbeat-based)
   - User A closes the tab / loses connection
4. A "Force unlock" action is available to any other user, with a confirmation modal warning that User A's unsaved changes may be lost. (Captured in the version history as an event.)
5. Top-of-document presence bar shows avatars of everyone currently viewing the artifact (read state + which section they hold a lock on, if any).
6. Save events broadcast to other connected clients so they see updated content without manual refresh.

**Transport:** WebSocket channel per artifact (`/ws/artifacts/{id}`) carrying:
- `presence` (join/leave/heartbeat)
- `lock_acquired` / `lock_released` / `lock_force_unlock`
- `section_saved` (triggers refresh of that section's content in other clients)

## Out of Scope (deferred)

These are deliberately punted to follow-up tickets:

- **Live cursor / character-level sync (Google Docs / CRDT / Yjs).** Explicitly rejected by user as MVP scope. May revisit if soft-locking proves too restrictive.
- **Merge UI** for the case where User A force-unlocks User B mid-edit. MVP just warns + discards.
- **Sub-section / paragraph-level locking.** MVP locks at the section boundary.
- **Offline editing + sync-on-reconnect.** MVP assumes online users.
- **Read-only viewer mode** as an explicit role. MVP treats anyone without lock as a viewer of that section.
- **Cross-section atomic edits** (e.g., a single edit that spans two sections).
- **Mobile/touch presence behaviour.**

## Technical Approach

**Backend (citemed_web):**
- New `artifact_section_locks` table: `(artifact_id, section_id, holder_user_id, acquired_at, last_heartbeat_at, expires_at)`.
- New `artifact_editor_sessions` table for presence: `(artifact_id, user_id, joined_at, last_seen_at, current_section_id NULL)`.
- WebSocket endpoint on the artifact editor route. Heartbeat every 15s; lock TTL 2 min from last heartbeat.
- Save endpoint validates the saver still holds the lock; rejects writes from non-lock-holders (returns 409 with current holder info).

**Frontend:**
- Vue/React component for the presence bar.
- Section components subscribe to lock state; non-holders rendered read-only with the holder banner.
- Force-unlock modal.
- WebSocket client with reconnect + exponential backoff.

**Coordination with ECD-1817 / ECD-1292:**
- The lock-holder model must reconcile with auto-save behaviour from ECD-1292. Recommend: auto-save fires only while lock is held; lock release flushes one final save.
- ECD-1817 should be fixed first or in parallel — fixing the data-loss bug while locking is in flight risks the lock model masking the original defect.

## Acceptance Criteria

- Two users open the same artifact; both see each other in the presence bar within 5s.
- User A clicks into Section X; User B sees Section X turn read-only with banner "User A is editing — Xs ago" within 2s.
- User A makes edits and saves; User B sees the updated section content within 2s (without manual refresh).
- User A walks away (no heartbeat for 2 min); lock auto-releases; User B can now edit.
- User B can force-unlock with confirmation; force-unlock event appears in the artifact's version/audit history.
- A save attempt by a user who does NOT hold the lock returns a clear error and does NOT clobber the section.
- Disconnecting (tab close, network drop) releases the user's locks within 30s.

## Estimate

Rough: **24–32 hours** of engineering (BE schema + WS + endpoints ~10h, FE presence + lock UI ~10h, force-unlock + audit ~4h, QA + edge cases ~4h).

This exceeds the playbook's MVP 4-hour target — flagging that **this is a Story-sized scope and should probably be split into a small Spike → Design → Implement chain** rather than implemented in one session. Recommendation in the triage section below.

**Critical path:** WebSocket infrastructure (if none exists in citemed_web for artifacts yet). If WS already exists for the Clio chat panel (ECD-1619 is in QA), reuse that transport.

## Dependencies

- **WebSocket infra:** Check whether ECD-1619 (FE Chat Panel + WebSocket Client + Artifact Rendering, currently in QA) provides a reusable WS client. If yes, big time saver.
- **Auth identity in WS context:** Need the user's identity available on the WS connection (likely already there, but verify).
- **ECD-1817 fix:** Should land first to avoid conflating data-loss debugging with concurrency debugging.
- **ECD-1292:** Auto-save behaviour AC needs to be locked down so the lock-release-flush handshake can be specified.

## Open Questions

- **Q1: What counts as a "section"?** Is it already a first-class concept in the editor data model, or do we need to derive section boundaries from the document structure? (Affects whether locking is even feasible at this granularity.)
- **Q2: Auto-save + locking interaction.** If User A holds a lock and is auto-saving every 5s, do other users see those incremental saves, or only the final one on lock release? (Recommend: only on release, to avoid flicker.)
- **Q3: What's the expected concurrent-user load per artifact?** 2–3 reviewers is very different from a 10-person open-edit session.
- **Q4: Is there an existing in-flight ticket for the *backend* concept of "section"?** If not, this story may implicitly require it.
- **Q5: Force-unlock — should it require a role (e.g., only the artifact owner or an admin can force-unlock)?** Or is anyone allowed with a confirmation modal?
- **Q6: Reuse ECD-1619's WS infra, or stand up a new WS namespace for artifact editing?**

## Why This Matters

The Artifact editor is a multi-stakeholder document workflow — authors, reviewers, approvers all touch the same document. Today, the editor is effectively single-user, which means coordination happens out-of-band (Slack: "are you in the doc?") and concurrent edits are a silent data-loss risk. Adding section-level locking + presence gives teams a safe way to work in parallel without committing to the full complexity of live collaborative editing, while leaving the door open to expand later if the soft-lock model proves too restrictive.
