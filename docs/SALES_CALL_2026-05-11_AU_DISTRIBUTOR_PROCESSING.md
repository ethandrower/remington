# Sales Call Processing — 2026-05-11 — AU Distributor (Anne Rocky / Cush)

**Processed by:** PM Agent (Remington)
**Source transcript:** pasted inline by user on 2026-05-11
**Call type:** demo + follow-up (Article Galaxy integration showcase + new-team intro)
**Playbook:** `docs/SALES_CALL_PROCESSING_PLAYBOOK.md`

---

## 1. Triage

### Participants — Citemed side
- **Ethan Drauer** — CEO (demo driver)
- **Tom Stanford** — CEO / founder of parent co (closer; on mobile audio-only)
- **Sares** — Operations Manager

### Participants — Prospect side
- **Anne Rocky** — Market Access & Reimbursement team (primary contact, repeat caller)
- **Cush** — Regulatory Lead (Anne's manager; joined late; asked the most product-shaping questions)
- **Susan** — Regulatory Associate (urology / asthma / complex recon)
- **Zanab** — Regulatory Associate (neurosurgery / peripheral / castrating reconstruction)
- **Nicole** — Marketing
- (One inaudible commuter participant)

### Account
- **Inferred:** Australian medical-device **distributor** (Anne: "we are a distributor, it's not actually our technology"). Multi-region (Melbourne HQ).
- **Size signals:** ~400 salespeople; this purchase = 5 execution users + 20–30 requester users (Cush).
- **Existing stack:** Article Galaxy (contact = "Mon"); Microsoft (Entra ID) for identity.

### Deal stage
**Mid-funnel demo, post-intro.** Anne had prior calls. New stakeholders added (Reg team + marketing). Deal moving toward trial → quote → contract.

### Outcome / sentiment
- Anne: *"I don't need any [more demo]. I'm happy with what I've seen today."*
- Cush: *"Likewise, and very encouraging."*
- Both committed to next steps. **Positive close.**

### Citemed-side commitments made on the call
1. Provision trial accounts (no purchase ability) — "give us a couple of days"
2. Send pricing quote (sizing: 5 execution + 20–30 requesters)
3. Send standard order form / MSA template — Cush wants legal review in parallel
4. Send IT FAQ + SSO/Entra ID setup docs to Cush's identity team
5. Next demo: pair **Search Notebook + Alerts** for the regulatory workflow specifically
6. Think through Cush's "forward-citation → vigilance" idea and circle back
7. Conform copyright stamp format to Anne's earlier spec (pre-prod tweak)

---

## 2. Signals extracted

### Customer pains / feature requests

| Speaker | Quote / paraphrase | Cluster |
|---|---|---|
| Cush | "Is there an approval workflow if the cost is going to be borne by a certain cost center?" | **A** Cost-center-routed purchase approval |
| Cush | "Is there a way to tag all the articles that are explicitly mentioned in a CER? So if any follow-ups to the articles or any editorials that mention those articles, those things are flagged to us." | **B** Predicate-article tagging + forward-citation surveillance |
| Cush | "Is there a way to link any future articles that get published to any tagging that we do to predicate articles?" | **B** (continued) |
| Cush | "Just a risk profile — based on what we know, it's been referenced once, low risk, or mentioned 20 times, in which case potentially something the business needs to review." | **C** Citation-volume risk scoring → vigilance queue |
| Cush | "Can the requesters see the commentary that we would have placed against an article? … if someone comes back to it three months later." | **D** Commentary visibility to requesters (validation moment — confirmed already supported) |
| Cush | "We've got 400 salespeople… guarantee they will find the same article three months after each other." | **E** Duplicate-request prevention UX |
| Anne | "Are we able to get on the platform ourselves and have a little play?" | **OP** (operational: trial accounts) |
| Anne | "Marketing is where I get the pixels [feature requests]" | context — marketing is a power user |
| Anne | "If I'm doing a SLR on clinical outcomes and exclude bench-test studies, those are sometimes important for commercial team for stupid reasons" | **F** Cross-list / cross-tag exclusion-visibility (already addressed; confirmation only) |
| Susan | "I just need to figure out how we'd use it on a more day-to-day basis. Regulatory generally needs to consider all papers regardless." | context — Reg team is not doing systematic reviews; needs lighter ad-hoc tooling |
| Susan | "We can use any articles we find to defend any investigations that TGA conducts." | context — use-case: TGA defense (regulatory traceability) |
| Anne | "If we have a product under investigation, set up an alert + SLR in preparation, just in case." | use-case validating alerts feature |

### Workflow details (context)

- **Anne's team workflow:** market access / reimbursement + commercial enablement. Approves marketing claims. Runs internal journal clubs.
- **Reg team workflow (Susan, Zanab, Cush):** regulatory submissions, TGA investigation defense, monitoring published evidence on already-approved devices. **Note:** they don't currently author CERs themselves (they're a distributor), but Anne flagged this as a future possibility.
- **Marketing workflow (Nicole):** ad-hoc lookups against own + competitor products. Needs commentary on prior exclusions to avoid revisiting.

### Competitive / integration mentions

- **Article Galaxy** — paid integration in motion via "Mon" (their contact). Citemed got expedited approval. Used today: 4 test purchases already racked up in Citemed's own demo billing.
- **Microsoft / Entra ID** — for SSO.
- **TGA** (Therapeutic Goods Administration, Australia) — regulator they defend submissions against.

### Validation moments (features they liked)

| Theme | Quote / context |
|---|---|
| Article Galaxy purchase flow | Anne: *"Yep, perfect"* on the cross-system billing question |
| Cross-project article history bubble | Cush: *"It in my mind it gets rid of the repeat kind of requests"* |
| Commentary persistence | Cush: *"That makes sense. That's exciting"* re: requesters seeing prior exclusions |
| Vigilance queue (live reviews) | Cush: *"That makes sense"* re: follow-ups landing in queue |
| Copyright stamping | Anne previously sent her own stamp spec — already committed to conform |
| Search Notebook (not shown, just mentioned) | Anne: *"And… marketing is where I get the pixels [requests]"* — directly fits |

### Citemed commitments / promises in the moment

- Ethan: "We could conform [copyright stamp] to whatever you want." → action item
- Tom: "Let us think about [forward-citation idea] a little bit." → idea capture
- Tom: "We know exactly what they'll ask [IT team] and we'll get it pulled together." → docs send

---

## 3. Dedup buckets

Dedup queries run via `trinity jira search` across **MDP** and **ECD** plus codebase grep on `citemed_web`. See queries inline.

### ✅ Already implemented (use as proof points / share in next call)

| Theme | Evidence | Customer signal |
|---|---|---|
| **Article Galaxy integration (purchase + auto-fetch)** | Live in demo env; MDP-88 (Delivery), ECD-1867/1868 (lifecycle improvements In flight) | Anne explicitly approved billing flow |
| **Copyright usage stamp on PDF download** | MDP-201 (Delivery), ECD-1599 (Complete) — ships First-Page stamp at download time | Anne sent her own spec; will conform |
| **Cross-project article history / "reviewed before by X"** | Shown on call; lives in Screening UI | Cush: "gets rid of repeat requests" |
| **Commentary persistence across requesters** | Permission system + history bubble | Cush: "that's exciting" |
| **Read-only / requester-vs-execution permission split** | `citemed_web/accounts/` has Permission model + group permissions | Ethan committed to it; Tom framed "requesters vs keepers"; need to verify "Requester" is packaged as a preset role (vs. ad-hoc permission set) |
| **AI-assisted search-term suggestions** | Implemented but **disabled in demo env** Anne saw — confirmed by Ethan on call. MDP-220 (Discovery) covers next-gen Clio-assisted version. | ⚠️ **Action item:** enable in trial environment |

### 🟡 On roadmap (MDP idea / ECD story exists; surface customer urgency)

| Theme | Existing ticket | Status | Customer urgency |
|---|---|---|---|
| **Search Notebook (ad-hoc search)** | MDP-165 "Quick Search & Add to Library" | Ready for delivery | **HIGH** — Anne flagged this fits Reg + marketing workflow better than full SLRs; Ethan committed to demo next call |
| **Search Notebook P2 improvements (multi-DB, AI extraction cols, staging)** | MDP-108 | Discovery | Medium |
| **Smart AI alerts / configurable notifications** | MDP-142 "Alerts & Notification Engine" | Discovery | **HIGH** — explicitly committed to deliver by onboarding; ECD-1792 "Edit Alert Configuration" Changes Requested |
| **Living Reviews → Vigilance Alerts consolidation** | ECD-1827 | In Progress | Medium — relevant to forward-citation surveillance idea |
| **Search-term recommendation system** | MDP-105 "Search Term Recommendations (incl history)" | Discovery | Medium |
| **Multi-DB search-syntax validation + MeSH** | MDP-125 | Discovery | Low (already works in demo) |

### 🔵 In flight (active ECD work — push to land before trial)

| Theme | Ticket | Status | Why it matters |
|---|---|---|---|
| Full-text download lifecycle (retry + backoff) | ECD-1867 | Draft | Reliability for AU trial article fetches |
| Full-text download admin visibility | ECD-1868 | Draft | Anne's "billing/account" tracking concern |
| Screening "Full Text Available" badge expansion | ECD-1911 | Draft | UX clarity in screening for trial users |
| CiteMed Open Access service | ECD-1909 | Draft | Cost reduction (free articles before paid Galaxy hits) |
| Living Reviews → Vigilance module consolidation | ECD-1827 | In Progress | Anchor surface for forward-citation idea (if filed) |
| Edit Alert Configuration | ECD-1792 | Changes Requested | Anne's onboarding requires alerts working |

### 🔴 Novel — candidates for `/idea`

Each one listed below cleared dedup against MDP + ECD + codebase + docs.

| ID | Theme | Recommended priority | Dedup queries run |
|---|---|---|---|
| **N1** | **Forward-citation surveillance → vigilance queue** ("when an article in our library is cited by a newly-published study, surface that cite in the vigilance queue with a risk score based on citation volume") | **P1** — Cush's explicit ask + regulatory traceability story |  `text ~ "cited by"`, `"forward citation"`, `"citing references"`, `"follow-up study"` — no direct match; SoTA classification (ECD-1854/1855) is different |
| **N2** | **Predicate-article tagging in CER / regulatory documents** (companion to N1: tag the articles your CER cited, so the system knows which articles to surveil for follow-ups) | **P1** — same dedup; tightly couples with N1 | `text ~ "predicate article"`, `"tag CER"`, `"article tag"` — no match |
| **N3** | **Cost-center-routed purchase approval workflow** (per-cost-center spend limits + routing of article-purchase approvals to the right approver) | **P2** — Cush's ask; ECD-680 "Fulfillment Workflow License Enhancement" Epic touches license metadata but does NOT cover cost-center routing | `text ~ "cost center"` → ECD-680/681; read both, neither covers routing |
| **N4** | **"Requester role" preset** — packaged read-only-plus-request role so customers don't have to configure permissions ad-hoc for commercial teams | **P3** — UX polish; underlying permissions exist | grep on `citemed_web/accounts/` confirms permission system but no "requester" preset role |
| **N5** | **Duplicate-request prevention UX in requester flow** (when a requester tries to buy an article already in the library or already requested, show inline) | **P3** — Cush's "400 salespeople will request the same article" scenario; not a Jira hit | `text ~ "duplicate request"` — no direct match |

### ⚪ Inconclusive

| Theme | Partial match | Question for user |
|---|---|---|
| Cost-center allocation **after purchase** (Anne: "we can then go to when we claim our expenses, allocate a division") | ECD-680/681 touch license metadata not allocation | Is this an Article Galaxy responsibility (already handled there per Mon), or does Citemed need to surface allocation hooks? |
| Word-template / READYVIE module | Deferred on call ("later discussion") | Already on roadmap (not searched in this pass); revisit when prospect is ready |

---

## 4. Customer profile — AU Distributor (Anne Rocky / Cush)

**Account profile**
- **Industry:** Medical-device distribution (not manufacturer; resells under master brand)
- **Region:** Australia (Melbourne HQ); multi-state coverage
- **Reg body:** TGA (Therapeutic Goods Administration)
- **Size signal:** ~400 sales-facing employees; 5 power-users + 20-30 requesters = the Evidence Cloud footprint

**Team structure**
| Role | Person | Workflow needs |
|---|---|---|
| Reg Lead | **Cush** | Approval workflow, governance, security review — decision-maker on contract |
| Market Access / Reimbursement | **Anne Rocky** | Day-to-day champion; runs Evidence reviews + journal clubs |
| Reg Associate (Urology/Recon) | **Susan** | TGA-investigation defense; light SLR needs |
| Reg Associate (Neuro/Peripheral) | **Zanab** | Regulatory submissions |
| Marketing | **Nicole** | Ad-hoc product/competitor article lookups; modular hip-stem context |
| Other commercial | (anonymous) | Requester tier; high volume, repeat-request risk |

**Tech stack signals**
- **Identity:** Microsoft Entra ID — SSO viable
- **Existing integrations:** Article Galaxy (Mon = their contact); intent to centralize fulfillment + billing
- **Compliance:** TGA-facing; will require security/IT review before contract

**Validation proof points (reuse in future calls / sales material)**
- Article Galaxy live purchase flow drew strong positive reactions
- Cross-project article history bubble triggered Cush's "gets rid of repeat requests" moment
- Requester-vs-Execution role split (Tom's framing) resonated with Cush
- Vigilance queue as a triage destination for surfaced events landed cleanly

**Objections / concerns raised**
- Cost-center cost allocation (resolved partially: handled in Article Galaxy)
- IT/security review before signing (standard — docs pending)
- Legal review of standard order form (Cush flagged; docs to be sent)
- Marketing access governance (Tom + Anne agreed: "requester" tier + read-only)

**Decision-making process**
- **Cush** = decision authority for regulatory / contract sign-off
- **Anne** = day-to-day champion and trial driver
- **Legal team** reviews MSA
- **IT team** reviews security / Entra ID setup
- **Order:** trial → quote review → legal review → IT review → contract

---

## 5. Action items

| # | Item | Owner | By when | Status |
|---|---|---|---|---|
| 1 | Provision trial accounts for AU team (no purchase rights) | Citemed (Ethan + Ops) | ~3 days | open |
| 2 | Enable AI search-term suggestions in trial env (works in prod) | Citemed eng | before trial start | open |
| 3 | Conform copyright stamp format to Anne's earlier spec | Citemed eng | pre-prod cutover | open |
| 4 | Send pricing quote (5 execution + 20–30 requester) | Citemed sales (Tom) | a couple of days | open |
| 5 | Send standard order form / MSA template | Citemed (Tom) | a couple of days | open |
| 6 | Send IT FAQ + Entra ID SSO setup docs to Cush's IT contact | Citemed (Tom) | a couple of days | open |
| 7 | Schedule follow-up demo: Search Notebook + Alerts (regulatory workflow) | Citemed (Ethan) | post-trial | open |
| 8 | Investigate forward-citation → vigilance feasibility and circle back to Cush | Citemed product (Tom + Ethan) | post-call | open |
| 9 | Capture Anne's earlier copyright-stamp spec to pre-prod ticket | Citemed eng | pre-prod cutover | open |

---

## 6. Recommendations to user

### File via `/idea` (top picks, in priority order)

1. **N1 + N2 combined: Predicate-Article Tagging + Forward-Citation Surveillance.** These two are inseparable — predicate tagging is the input mechanism; forward-citation surveillance is the output. Recommend filing as **one MDP Idea** ("Citation-Aware Vigilance: Predicate Tagging + Forward-Citation Surveillance for Regulatory Traceability"). Cush gave a concrete scenario (TGA flagged a phase-2 follow-up of a phase-1 they cited; client missed it). This is regulatory-grade differentiation and aligns with the in-flight **ECD-1827 "Living Reviews → Vigilance Alerts"** epic, so it has a natural delivery home.

2. **N3: Cost-Center-Routed Purchase Approval Workflow.** Stand-alone P2. Should link "relates to" **ECD-680 "Fulfillment Workflow License Enhancement"** since they touch the same purchase surface but at different layers.

### Don't file (yet)

- **N4 (Requester role preset)** — UX polish, can be solved with documentation + customer-success scripts for trial. File only if the trial reveals friction.
- **N5 (Duplicate-request UX)** — likely a small follow-up to MDP-88 (in Delivery). Surface to whoever owns MDP-88 rather than open a new idea.

### Worth showing in next demo (per Citemed commitment)

- **Search Notebook (MDP-165 Ready for delivery)** — Anne explicitly said this fits her team better than full SLR
- **Alerts UI (ECD-1792, ECD-1827)** — Anne wants them at onboarding time
- **Live Reviews → Vigilance consolidation (ECD-1827 In Progress)** — directly relevant to the forward-citation pitch

### Surface to deal team

- **Trial-environment configuration gap:** AI search-term suggestions aren't enabled in the demo env. If we hand AU the trial account and suggestions are off, that's a poor first impression. Verify before provisioning.
- **Customer is explicitly evaluating us against a "consolidated procurement + storage" mental model.** Anne's question "if we leave Article Galaxy, do we keep our PDFs?" tells us **ownership / lock-in fears are a buying criterion.** Sales should reinforce: PDFs are exportable; we don't trap.
- **Cush is the deal-maker.** Loop him into the trial review explicitly. He asked the highest-signal product questions and articulated specific regulatory pain points.

### Risks to flag

- **TGA-defense use case is a non-trivial differentiator.** If we win this account, we'll be cited as a TGA-defense tool — make sure feature-set supports it (predicate tagging especially).
- **Legal / IT review can stretch the cycle.** Tom committed to sending materials in "a couple of days." Track that — slipping = momentum loss.

---

## Appendix: queries run

```
trinity --json jira search 'project in (MDP, ECD) AND text ~ "search notebook"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "smart alert"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "AI alert"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "ad hoc search"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "copyright stamp"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "search term suggestion"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "approval workflow purchase"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "cost center"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "cited by"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "forward citation"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "citing references"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "predicate article"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "follow-up study"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "requester role"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "read-only"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "duplicate request"'
trinity --json jira search 'project in (MDP, ECD) AND text ~ "Article Galaxy"'

# Code grep:
grep -rln "read.only\|readonly\|RequesterRole\|requester_role\|approve_purchase\|purchase_approval" citemed_web/

# Tickets read in full:
ECD-680, ECD-681, MDP-201, MDP-165, MDP-108, MDP-220, MDP-142, MDP-88
```

**Caveat:** Did not exhaustively dedup every micro-utterance. Focused on themes that produced ≥2 utterances or specific feature asks. If you want me to drill into a specific theme harder, point at the row.
