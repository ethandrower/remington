# Cost-Center-Routed Purchase Approval Workflow - Proposal

**Date:** 2026-05-11
**Author:** PM Agent (Remington) + Ethan Drower
**Status:** Proposal / Ready for build-out
**Origin:** Sales call 2026-05-11 — AU Distributor (Cush, Regulatory Lead)
**Adjacent epics:** ECD-78 (Full Text Request Workflow, In Progress) · ECD-680 (Fulfillment Workflow License Enhancement, Draft)

---

## Origin

Cush (Regulatory Lead at the AU distributor prospect) explicitly asked on 2026-05-11:

> "Is there an approval workflow if the cost is going to be borne by a certain cost center? Is there an ability to seek approval within the platform?"

Ethan answered today: per-user permission to accept/reject or send-for-approval, but **not split by cost center**. Tom committed to operationalizing whatever they explain. Cush followed up immediately with a "20–30 requesters / 5 execution users" sizing — confirming they want to roll this out to a *requester tier* across a 400-person commercial team, with budget governance.

This is a P2 differentiator for a deal Cush is the decision-maker on, and it's a fit-for-purpose feature that any multi-cost-center org will want once they expand seat counts.

## Current State

Article-purchase request → fulfillment flow lives in `citemed_web/`:

- **`lit_reviews/models/requests.py`** — `Request` (parent) → `FullTextArticleRequest` → `FullTextOrder` (Article Galaxy / provider order record).
- **`citesource/api/views/user_requests.py`** — `RequestFullTextAPIView` (Create), `CancelFullTextRequestAPIView`, `RequestsListAPIView`, etc.
- **Approval today:** governed at the user-permission level (`accounts/` has the Permission model). Per-user "can purchase / can approve / must request approval." No first-class cost-center entity, no spend limits, no routing rules.
- **Adjacent in-flight work:**
  - **ECD-78** Full Text Request Workflow — the parent workflow our changes plug into.
  - **ECD-680** Fulfillment Workflow License Enhancement — admin/fulfiller license-metadata layer. Different concern (license type tracking, not approval/budget). **Link as "relates to"; don't nest under.**

Today the prospect's question is operationally impossible: a 25-requester roster cannot all share one approval queue with no budget visibility.

## User Requirement

> "We may have how many sales reps we have? About five [execution users]. Probably 5 that will be the execution users, but potentially 20 to 30 that are going to be like requesters."
> — Cush, 2026-05-11

Concretely, the AU distributor needs:
1. **Cost centers as first-class entities** (different commercial / regulatory / marketing divisions).
2. **Users assigned to one or more cost centers.**
3. **Spend caps per cost center** (annual / monthly / per-purchase — exact granularity TBD).
4. **Approval routing** — when a requester submits a purchase, route to the right cost-center approver. Auto-approve below threshold; require approver above.
5. **Audit trail** — who requested, who approved, which budget got debited.
6. **Per-cost-center reporting** — total spend over a date range.

## Proposed Solution — MVP

**Scope guardrail:** ship the *minimum* version that lets a prospect like AU Distributor model their 25 requesters against 3–5 cost centers with one approver per. Defer reporting dashboards, advanced budget models (rollover, quotas, etc.), and multi-tier approver chains.

### MVP feature set

1. **`CostCenter` model** — name, code, owner (User FK → approver), parent organization (org-scoped), is_active. CRUD via admin first; minimal UI surface.
2. **`UserCostCenterMembership`** — M2M with `is_default` flag. A user can request against any cost center they belong to; one default for pre-selection.
3. **`CostCenterBudget`** — period (`monthly` / `annual`), amount, currency, effective dates. One active budget per cost center per period.
4. **`CostCenterSpend`** — running aggregate, recomputed/incremented on each fulfilled purchase. Persisted for fast reads + tamper-evidence.
5. **`RequestApproval`** — links to `FullTextArticleRequest` + cost center + approver user + state (`pending`, `approved`, `rejected`, `auto_approved`) + reason. Created at request time.
6. **Request flow change:**
   - Requester picks a cost center (defaults to their default) on `FullTextArticleRequest` create.
   - System checks: does this purchase amount + period-to-date spend exceed `CostCenterBudget.amount`?
     - **Under threshold + requester has direct-purchase permission** → auto-approve, place order.
     - **Otherwise** → state goes `pending`, approver gets notified, order placement is gated.
7. **Approver UI** — a dashboard view ("My Approvals Queue") showing pending approvals across cost centers they own. Approve/reject inline. Approval triggers order placement.
8. **Cost-center field on `FullTextOrder`** — denormalized at fulfillment time for reporting.
9. **Audit log entries** for every state transition on `RequestApproval` (request, approve, reject, auto-approve).

### What this *isn't* (deliberate)

See "Out of Scope" below — kept tight on purpose. The point is to get cost-center routing + spend governance shipped, not to build a procurement suite.

## Out of Scope (deferred)

- **Multi-tier approver chains** (manager → director → VP). MVP = one approver per cost center.
- **Spending dashboards / charts.** API endpoint exposes the data; UI in a follow-up.
- **Per-user spend limits independent of cost center.** Possible follow-up if a customer asks.
- **Budget rollover, soft caps, hard caps with override.** MVP = hard cap with approver bypass via approve action.
- **Multi-currency normalization.** MVP = one currency per cost center; same-currency requests only.
- **Cost allocation *after* purchase** (Anne's question — Article Galaxy handles this side). Keep tracking it but no Citemed-side feature.
- **Bulk-approve UX, batch ops.** Single approve/reject per request to start.
- **External AP / ERP integration** (NetSuite, etc.). Out of scope; surfaces only via reports / CSV export.
- **License metadata** — that's ECD-680's territory; we cross-link, don't duplicate.

## Technical Approach

### Data model deltas

```
CostCenter
  - id (PK)
  - organization (FK → Organization)
  - name (str)
  - code (str, unique within org)  # for AP / GL references
  - approver (FK → User)
  - is_active (bool)
  - created_at, updated_at

UserCostCenterMembership
  - user (FK → User)
  - cost_center (FK → CostCenter)
  - is_default (bool)
  - Meta: unique_together (user, cost_center)

CostCenterBudget
  - cost_center (FK → CostCenter)
  - period (enum: monthly | annual)
  - amount (Decimal)
  - currency (str, default 'USD')
  - effective_from, effective_to (DateField)

CostCenterSpend  # rolling aggregate, period-scoped
  - cost_center (FK → CostCenter)
  - period_start, period_end (DateField)
  - amount_spent (Decimal)
  - last_updated (DateTime)
  - Meta: unique_together (cost_center, period_start)

RequestApproval
  - request (OneToOne → FullTextArticleRequest)
  - cost_center (FK → CostCenter)
  - approver (FK → User, nullable)         # null if auto-approved
  - state (enum: pending | approved | rejected | auto_approved)
  - reason (text, nullable)                 # filled on reject
  - requested_at, decided_at (DateTime)
```

### API surface

- `GET    /api/cost-centers/`             — list, scoped to user's org
- `POST   /api/cost-centers/`             — create (admin only)
- `PUT    /api/cost-centers/{id}/`         — update
- `GET    /api/cost-centers/{id}/spend/`   — current-period spend + remaining budget
- `GET    /api/cost-centers/{id}/members/` — user list
- `POST   /api/cost-centers/{id}/members/` — assign / unassign

- `POST   /api/requests/fulltext/` (extend existing) — accepts `cost_center_id`
- `GET    /api/approvals/?state=pending&approver=me` — approver's queue
- `POST   /api/approvals/{id}/approve/`
- `POST   /api/approvals/{id}/reject/` (body: `{"reason": "..."}`)

### Behavior at request-create time

```
on FullTextArticleRequest create:
    cost_center = payload.cost_center_id or user.default_cost_center
    estimated_cost = lookup_from_provider(article)   # Article Galaxy quote, or 0 if OA
    current_spend = CostCenterSpend.for_period(cost_center, today)
    budget       = CostCenterBudget.active_for(cost_center, today)

    if estimated_cost == 0:                                # OA → free
        state = 'auto_approved'
    elif user.has_perm('direct_purchase') and current_spend + estimated_cost <= budget.amount:
        state = 'auto_approved'
    else:
        state = 'pending'
        notify(cost_center.approver, request)

    create RequestApproval(state=state, ...)
    if state == 'auto_approved':
        place_order(request)                              # existing flow
```

### Behavior at approve action

```
on approve(request_approval):
    if approval.state != 'pending':                       # idempotency
        return 409
    approval.state = 'approved'
    approval.decided_at = now()
    approval.approver = current_user
    place_order(approval.request)                         # existing flow
    increment CostCenterSpend(cost_center, period, estimated_cost)
    audit_log('approval.approved', ...)
```

### Migration / rollback

- Brand-new models — pure additive migration. No data migration for existing requests (back-compat: requests without `RequestApproval` continue to behave as today; auto-approve at the request-create-API layer only when feature is enabled per org).
- **Feature-flag the routing on org level** (`Organization.cost_center_approval_enabled` bool). Orgs without it opted-in still see today's behavior. AU Distributor flips to on at trial provisioning.
- Rollback: disable the flag; no data destruction.

### Frontend surfaces (Vue)

1. **Request form** — add cost-center dropdown above article; defaults to user's default. Show "remaining budget for [cost center] this month: $X" inline.
2. **Approver dashboard tab** — new "Approvals" tab with pending queue. Inline approve/reject. Show requester, article, estimated cost, cost center, budget impact.
3. **Admin panel** — `CostCenter` CRUD in the org admin section. User-membership management in the existing user admin row.
4. **Notification** — email to approver on new pending request; in-app toast / notification center entry if those exist.

## Acceptance Criteria

1. **Cost center CRUD** works end-to-end; org admin can create / edit / deactivate cost centers; assign approver.
2. **User-cost-center membership** with a default; users see only cost centers they're members of in the request form.
3. **Budget enforcement:** a requester whose cost center is at-cap cannot auto-approve; their request goes to `pending` regardless of permission level.
4. **Auto-approve path:** OA articles + below-cap+permitted users skip approver entirely; order placed within current Article Galaxy flow latency budget.
5. **Approver path:** approver sees pending request in their queue within 30s of submission; approve places the order, reject emails the requester with the reason.
6. **Spend tracking:** `CostCenterSpend` increments correctly on each `FullTextOrder` finalize; survives concurrent approvals (transactional update).
7. **Audit trail:** every state transition logged with actor + timestamp + reason; queryable via existing audit log surface.
8. **API export:** GET `/api/cost-centers/{id}/spend/?from=YYYY-MM-DD&to=YYYY-MM-DD` returns the period's purchase records for offline reporting.
9. **Feature-flag gate:** orgs with `cost_center_approval_enabled = False` see zero behavior change from today.
10. **Backward compat:** existing in-flight requests (created before migration) continue to fulfill without error.

## Estimate

**Total: 24–32 hours, split into 5 child stories.** Each story ≤ 8h, build-shippable independently behind the feature flag.

| # | Story | Est. | Critical-path |
|---|---|---|---|
| 1 | BE: data models + migrations + admin CRUD (`CostCenter`, `UserCostCenterMembership`, `CostCenterBudget`, `CostCenterSpend`, `RequestApproval`) | 6h | Yes — blocks all downstream |
| 2 | BE: extend `FullTextArticleRequest` create → branch into auto-approve / pending; cost-quote lookup; `RequestApproval` row creation | 6h | Yes — blocks FE wire-up |
| 3 | BE: approval API (`/api/approvals/...`), notification stub, transactional `CostCenterSpend` increment | 6h | No (parallel to 4) |
| 4 | FE: request form cost-center dropdown + remaining-budget hint | 4h | No |
| 5 | FE: Approver dashboard tab + approve/reject actions; audit-log entries surfaced | 6h | No |
| (buffer) | E2E test on staging + AU trial smoke | 2–4h |  |

**Critical path:** Story 1 → Story 2. Stories 3-5 parallelize once data model lands.

## Dependencies

- **ECD-78** Full Text Request Workflow — our request-time branching plugs into this. Coordinate with whoever owns ECD-78 so we don't conflict at the create endpoint.
- **ECD-680** Fulfillment Workflow License Enhancement — touches the same fulfillment surface. Coordinate serializer / model migrations to avoid clashing migrations. Link as "relates to."
- **Notification subsystem** — assumed in place (email + in-app). If neither exists, add a stub that logs to the existing audit trail and ships email-only behind a separate flag.
- **Article Galaxy cost lookup** — we need an `estimated_cost` at request-create time. If Article Galaxy's "availability check" call already returns price (per the demo it does), we use that. If not, we need to call it explicitly in the request-create path. **Verify before story 2 starts.**

## Open Questions

1. **Granularity of budget period.** Monthly or annual? AU Distributor wasn't specific. Recommend: MVP = monthly with annual as a follow-up.
2. **Multi-currency.** AU is AUD; Citemed default is USD. Do existing orders track currency anywhere today? If not, scope a single-currency-per-org MVP and add USD↔AUD conversion as a follow-up.
3. **Approver self-approval.** Should a cost-center approver be able to auto-approve their own purchases up to the budget cap? Most enterprises allow this with audit-log notation. Recommend yes.
4. **Below-cap "direct purchase" permission.** Is this a new permission we're adding, or do we lean on the existing `can_purchase`? Likely: existing permission, semantics extended.
5. **Approval queue notification cadence.** Real-time vs. digest? MVP = email per new request + in-app entry; revisit in customer-success feedback.
6. **How does this interact with the per-user accept/reject system Ethan mentioned on the call?** Need to read the current permission code to confirm we're augmenting cleanly, not duplicating.

## Why This Matters

**Sales-cycle differentiator.** Cush is the decision-maker on a hot deal and asked for this explicitly. Tom committed Citemed to operationalize it. Shipping this in the AU trial window converts "is this a fit for our 400-person commercial team?" into "yes."

**Recurring buyer requirement.** Any prospect with > ~10 commercial users will ask for budget governance. Today we have no answer; this gives us one.

**Adjacent to ECD-680 / ECD-78.** Three pieces of fulfillment-flow work shipping in close succession means a coordinated release window, which is operationally easier than relitigating the same fulfillment surface three quarters apart.

---

## Recommended Build-out Structure

### File as **one MDP Idea (Discovery)** to anchor the concept:
- **Title:** "Cost-Center-Routed Purchase Approval Workflow"
- **Body:** abridged version of this proposal (problem + MVP scope + acceptance criteria summary), link to this doc.
- **Priority signal:** P2 (sales-cycle driver, not a P0 incident)
- **Link:** "relates to" ECD-78, ECD-680

### Then file **one ECD Epic + 5 child Stories** when promoted to delivery:
- **Epic title:** "Cost-Center-Routed Purchase Approval Workflow"
- **Stories** (one per row in the estimate table above), each with its own acceptance subset of the criteria.
- Apply **feature flag `cost_center_approval_enabled`** so the epic can be merged in slices without exposing partial UX to non-AU customers.

### Triage recommendation

- **Discovery (now):** file MDP Idea + this doc as the artifact.
- **Delivery (this sprint or next):** if AU trial is provisioned in the next ~10 days, the Epic should be in the sprint that overlaps the trial — otherwise we risk Cush losing momentum waiting.
- **Effort:** 1 dev × 3–4 days, or 2 devs × 2 days with the BE/FE split.

## Filing blocker

Same as the earlier search-protocol idea: remington service account has 403 on MDP `Create Issues`. Either you file the MDP Idea from your account (paste the abridged body), or grant remington Create permissions so I can file MDP + the eventual ECD Epic + child stories programmatically.
