# Sales Call / Demo Processing Playbook

How the PM agent turns a raw call/demo transcript into structured product signal: new ideas, validated features, deal context, action items.

This playbook is **upstream of** `docs/PRODUCT_PROCESS.md` (idea-intake). Sales calls dump many candidate signals at once. This playbook triages them and feeds the genuinely-novel ones into `/idea` one at a time.

---

## When this playbook triggers

Anytime the user pastes (or links) a transcript and says any of:
- "Analyze this call / demo / transcript"
- "Process this and find ideas"
- "What's actionable from this call?"
- Or invokes a future `/call` slash command

The agent does **not** start filing tickets immediately. It produces a structured analysis doc, surfaces candidate novel ideas, and waits for user confirmation before invoking `/idea` on any of them.

---

## Output artifact

A single markdown file at:

```
docs/SALES_CALL_<YYYY-MM-DD>_<SHORT_LABEL>_PROCESSING.md
```

Where `<SHORT_LABEL>` is a memorable identifier (prospect company, lead contact, deal name). Example: `docs/SALES_CALL_2026-05-11_AU_DISTRIBUTOR_PROCESSING.md`.

The doc uses the template at the bottom of this playbook.

---

## The five stages

### Stage 1 — Triage (who, what, when, status)

Extract:

- **Date** (from header or inferred)
- **Participants** — split into "Citemed side" vs "Prospect side." For each: name + role/title if stated.
- **Deal context:**
  - Account name (or best inference)
  - Industry / region / size signals
  - Deal stage (intro, demo, follow-up, late-stage, contract review)
  - Decision-makers identified
- **Outcome / sentiment:** verbatim quotes if the prospect explicitly approved or rejected. Note tone shifts.
- **Citemed-side commitments made on the call** (anything Citemed said "we'll do X" or "we'll send Y").

### Stage 2 — Signal extraction (classification pass)

Walk the transcript top-to-bottom. For each non-trivial statement, classify into one of:

| Signal type | What it looks like | Where it goes |
| --- | --- | --- |
| **Customer pain** | "We currently have to do X manually" / "the problem is Y" | → Stage 3 dedup |
| **Feature request** | "Can the platform do X?" / "Could we have Y?" | → Stage 3 dedup |
| **Workflow detail** | Describes their current process. Useful context. | → Stage 4 customer profile |
| **Competitive / integration mention** | They use X today / they have Y in place | → Stage 4 customer profile |
| **Citemed commitment** | "We'll send you / we'll get back to you / we'll deliver by" | → Stage 5 action items |
| **Operational ask** | Quotes, contracts, SSO, security review, account setup | → Stage 5 action items |
| **Risk / objection** | Compliance, budget, IT review, change management | → Stage 5 action items |
| **Validation moment** | Customer explicitly likes / approves an existing feature | → Stage 4 proof points |

Be specific. Cite the speaker and (where possible) the timestamp or a short quote.

### Stage 3 — Dedup (for each candidate idea from Stage 2)

This is the heavy lift. **Cluster related signals first** — don't run dedup on every single utterance. Aim for 5–10 distinct themes per call.

For each theme:

1. **Jira MDP** (ideas / discovery):
   ```
   trinity --json jira search 'project = MDP AND text ~ "<keyword>"' --max-results 10
   ```
2. **Jira ECD** (already-scoped delivery work):
   ```
   trinity --json jira search 'project = ECD AND text ~ "<keyword>"' --max-results 10
   ```
   Also check recently-completed (`status = Done AND updated > -90d`) — the customer may be asking for something we just shipped and they haven't seen yet.
3. **Codebase** (citemed_web / citemed_ai):
   ```
   grep -rln "<keyword>" /Users/ethand320/code/citemed/citemed_web --include="*.py" --include="*.vue" 2>/dev/null
   ```
4. **Docs** (prior proposals):
   ```
   grep -rln "<keyword>" docs/ memory/ 2>/dev/null
   ```

Bucket each theme into exactly one of:

- **✅ Already implemented** — feature exists, just needs surfacing/training/screenshot for customer
- **🟡 On roadmap** — there's an open MDP idea or ECD story covering it; link
- **🔵 In flight** — has an active ECD ticket; link + note status
- **🔴 Genuinely novel** — no match anywhere → candidate for `/idea`
- **⚪ Inconclusive** — partial match; needs human judgment

**Discipline:** don't claim "novel" without showing the dedup queries you ran. The doc must include the dedup evidence so the user can audit.

### Stage 4 — Customer profile capture

For each call, build/update a section that captures durable context about the prospect/customer:

- Account name + region
- Team structure (named contacts → roles)
- Tech stack (identity provider, existing integrations they pay for, blockers)
- Use-case profile (regulatory? marketing? both? what modules of Evidence Cloud matter?)
- Validation proof points (features they explicitly liked → reuse in future calls)
- Objections / concerns raised (security, compliance, budget)
- Decision-making process (legal review, IT review, who signs)

This is durable across calls. If this account has had prior calls, reconcile against the prior doc.

### Stage 5 — Action items + commitments

Surface a flat list of operational follow-ups, with owner + due-by:

- Quotes / pricing to send
- Contracts / MSAs to share
- Security / SSO docs to deliver
- Trial accounts to provision
- Follow-up demos to schedule
- Specific bug fixes promised
- Specific feature commits made on-call

**These are not Jira tickets in MDP/ECD.** They are CRM-style action items. If the team uses a CRM, they go there. Otherwise capture in the processed-call doc.

---

## Output template

Save to `docs/SALES_CALL_<YYYY-MM-DD>_<LABEL>_PROCESSING.md`:

```markdown
# Sales Call Processing — <DATE> — <ACCOUNT/LABEL>

**Processed by:** PM Agent (Remington)
**Source transcript:** <link or "pasted inline by user on YYYY-MM-DD">
**Call type:** intro / demo / follow-up / contract review

---

## 1. Triage

**Participants — Citemed side:**
- Name (role)
- ...

**Participants — Prospect side:**
- Name (role) — region/team
- ...

**Account:** <name>, <region>, <industry>, <size signals>
**Deal stage:** <intro/demo/etc.>
**Outcome / sentiment:** <quote + assessment>

**Citemed-side commitments made on the call:**
- ...

---

## 2. Signals extracted

### Customer pains / feature requests
- (speaker) "<quote>" → theme X
- ...

### Workflow details (context)
- ...

### Competitive / integration mentions
- ...

### Validation moments (features they liked)
- ...

---

## 3. Dedup buckets

### ✅ Already implemented
| Theme | Evidence | Customer signal |
|---|---|---|
| Article Galaxy purchase flow | live in demo env, ECD-XXX | "<quote>" |

### 🟡 On roadmap (MDP/ECD idea exists)
| Theme | Existing ticket | Status | Customer urgency |
|---|---|---|---|
| ... | MDP-XXX | Discovery | high — explicit ask |

### 🔵 In flight
| Theme | ECD ticket | Status |
|---|---|---|
| ... | ECD-XXX | In Progress |

### 🔴 Novel — candidates for /idea
| Theme | Why novel (dedup queries) | Recommended priority |
|---|---|---|
| ... | searched MDP + ECD for X, Y, Z — no matches | P1 |

### ⚪ Inconclusive
| Theme | Partial match | Question for user |
|---|---|---|
| ... | MDP-XXX overlaps but is broader | "Is this the same scope?" |

---

## 4. Customer profile

(populated/updated per stage 4)

---

## 5. Action items

| Item | Owner | By when |
|---|---|---|
| Send quote (N users) | Citemed | next 3 days |
| ... | ... | ... |

---

## 6. Recommendations to user

- **File via /idea:** <novel theme 1>, <novel theme 2> (top 2-3 only)
- **Worth showing in next call:** <features that fit prospect's stated workflow but weren't shown>
- **Risks to flag to deal team:** ...
```

---

## Anti-patterns

| Anti-pattern | Why it's bad |
|---|---|
| Auto-filing Jira tickets without user review | Sales calls produce noise; not every utterance is a real ask |
| Claiming "novel" without dedup evidence | Wastes engineering time on duplicates |
| Skipping the customer profile section | Loses durable context between calls |
| Filing every Citemed commitment as a Jira ticket | Action items ≠ product work; mixing them clutters the backlog |
| Splitting one theme into many tickets | One coherent feature ask → one MDP idea; don't fragment |
| Ignoring "we already do that" responses on-call | These are validation points — capture them for future sales material |

---

## Notes

- A "theme" can collect 2–6 individual utterances if they're the same ask voiced multiple ways.
- When the customer's ask overlaps with a feature in `[QA]` or `[Draft]` status: that's a strong signal to push the existing ticket — note it, surface to the dev team.
- Keep the call-processing doc separate from any per-idea proposal docs. Cross-link, don't duplicate.
- The novel-ideas list at the end is a **recommendation**, not an action. User confirms which to push through `/idea` before any Jira tickets get created.
