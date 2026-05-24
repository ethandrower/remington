# Clio Chat-With-Paper on the Extractions Page — Proposal

**Date:** 2026-05-20
**Author:** PM Agent + Ethan Drower
**Status:** Discovery / Shape-decision pending

---

## Origin

Ethan asked on 2026-05-20: "Wouldn't it be cool if users could open Clio on the extractions page and chat with their paper in a useful way?" Two capability buckets named:
1. NL/semantic search across the paper's sections so users can ask things like *"find the section on results"* — answers must ground to a specific location in the document.
2. KB-backed guidance for the extraction/review workflow itself — e.g. *"what would you GRADE this article as in terms of evidence type?"* — Clio reads internal SOPs / MEDDEV / MDR / GRADE guidance and explains the reasoning.

User's framing: "Most of the chat-related things would need to be grounded in a specific location of the document for the user to feel like there's any credibility here at all."

## Current State

**Clio platform (already in flight):**
- **ECD-1652** *Clio (Copilot) — Context-Aware Agentic AI Assistant* (Epic, Ready for Development). Parent epic for the whole Clio stack.
- **ECD-1619** *FE: Chat Panel + WebSocket Client + Artifact Rendering* (Story, **in QA**). Provides the reusable chat-panel UI, Django Channels WS transport, 8 streamed artifact types (`summary_table`, `extraction_table`, `search_results`, `selection_list`, `template_picker`, `recipient_picker`, `tag_confirmation`, `share_confirmation`), session selector, inline-trigger buttons.
- **ECD-1815** *Clio (Copilot) — Artifact Editor Integration* (Story, In Refinement, under ECD-1284 Artifact Writer UX). Closest analog — Clio on the **artifact editor** (CER/PSUR drafting): section summaries, editorial comments, GSPR support check, literature sufficiency check, Notified-Body QC checklist. **Different surface** from this proposal.
- **MDP-220** *Clio — AI-Assisted Search Term Strategy* (Discovery). Same architectural shape-question this proposal faces.
- **MDP-213** *Strata Knowledge Graph* (Discovery). Lists "Clio over Strata" as anticipated child MDP — long-horizon framing.

**Extractions page (the target surface):**
- Vue page: `citemed_web/src/pages/lit_reviews/clinical-appraisal/ClinicalAppraisalApp.vue` plus `components/PdfJsViewer.vue` and `components/FullTextViewer.vue`.
- Data model: `lit_reviews/models/extractions.py`. Spatial grounding already exists — migration `0300_appraisalextractionfield_highlight_locations.py` adds per-extraction-field `highlight_locations`, and `0347_appraisalextractionfield_ai_evidence_quote.py` adds the AI's evidence quote. So *we already store the bbox/region for each AI-extracted field that links back to the PDF*. This is the primitive grounding can ride on.
- AI extractor: `citemed_ai/citemed_ai/services/extractor/*` already produces per-field extractions with span citations.

**What does NOT exist:**
- A semantic index over a paper's parsed *sections* (results / methods / discussion / etc.) for free-text NL queries.
- A KB ingest of internal extraction SOPs, MEDDEV/MDR guidance, GRADE methodology in a form Clio can cite.
- A "chat panel attached to the extractions page" surface — ECD-1619's panel today is built around the find/analyze/organize studies flows, not per-paper Q&A.

## User Requirement

Two grounded capabilities on the extractions page:

**A. Chat with this paper, grounded in document location.**
- *"Find the section on results."* → Clio scrolls/highlights the corresponding section in the PdfJsViewer.
- *"What sample size did they report?"* → answer + jump-to-bbox.
- *"Does this paper compare against any predicate devices?"* → answer + citations into the PDF.
- Every answer references a specific document region (page + bbox or section anchor) so the reviewer can verify in one click.

**B. Chat about how to perform this extraction / review, KB-grounded.**
- *"What would you GRADE this article as?"* — Clio applies the GRADE methodology, cites the guidance document section it used, and (where applicable) re-uses fields the AI already extracted.
- *"How do I extract `primary_outcome_measure` correctly?"* — Clio reads the internal SOP for that field and walks the user through it with the paper in front of them.
- *"Is this study design consistent with what MEDDEV 2.7/1 rev.4 requires for a Class III CER?"* — Clio reads MEDDEV and cross-references against the AI-extracted study-design field.

Hard constraint from the user: **credibility = grounding**. Ungrounded chat is not acceptable.

## Proposed Solution — MVP

> ⚠️ This is a Discovery proposal. Recommend **MDP Idea + spike**, not immediate implementation, for the same reason MDP-220 sits in Discovery: the architectural shape (separate agentic loop vs. Clio agentic loop vs. hybrid) is unresolved and is best decided after ECD-1619 lands and ECD-1815's shape becomes concrete.

Two parallel tracks. Track 1 is the smallest possible thing that proves grounding; Track 2 is the smallest thing that proves KB-citation.

**Track 1 — Paper Q&A with section grounding (MVP):**
1. Extend the existing per-paper parse pipeline (in `citemed_ai`) to emit **section-level chunks** (title, body text, page range, bbox-span) alongside extracted fields. Persist on `AppraisalArticle` (or sibling table).
2. Embed each chunk with `text-embedding-3-large` (or the model the rest of the codebase uses); store vectors in pgvector (already a peer-dependency from MDP-213's premise).
3. On the extractions page, mount the **existing ECD-1619 chat panel** as a tab/sidebar scoped to *this paper*. Add a new tool: `find_in_paper(query)` → returns top-k chunks with bbox + section anchor.
4. When Clio answers with a chunk-citation, the FE renders an inline trigger that scrolls + highlights the region in `PdfJsViewer.vue`.

**Track 2 — KB-grounded extraction guidance (separate MVP):**
1. Pick ONE internal KB to ingest first — recommend **GRADE methodology** (smallest, well-bounded, high-value question per user's example).
2. Chunk + embed into pgvector under a `KnowledgeArticle` table (typed: `methodology` / `meddev` / `mdr` / `sop_extraction_field`).
3. New tool: `consult_kb(question, kb_filter)` → returns top-k passages with source title + section.
4. New composite tool: `grade_this_article()` → uses existing AI-extracted study-design / outcome fields + `consult_kb(kb_filter='grade')` to produce a GRADE classification with cited reasoning.
5. Clio answers cite both the KB passage AND the underlying extraction field — two layers of grounding.

Each track is independently shippable. Track 1 alone is "talk to your paper." Track 2 alone is "ask Clio to GRADE this for you." Both together is the full vision.

## Out of Scope (deferred)

- **Cross-paper Q&A** ("compare this paper to the other 12 in my review"). MVP is single-paper scope.
- **Editing the extraction fields from Clio.** Read-only suggestions only in MVP; write actions wait until ECD-1815-style confirmation flows are settled.
- **Full MEDDEV/MDR ingest.** GRADE first, others later.
- **Forward-citation surveillance** — already deferred under `memory/project_citation_vigilance_deferred.md` pending Strata KG framing.
- **Voice / multimodal.** Text only.
- **Section-segmentation accuracy QA.** Use the parser's existing best-effort sections; section quality becomes a follow-up.
- **Clio writing extractions** — adjacent but distinct; that's a separate idea worth its own MDP.
- **Coverage of every AI-extraction field with a SOP explanation.** Pilot with 3–5 high-confusion fields.

## Technical Approach

**Backend (citemed_web + citemed_ai):**

| Component | Where | Notes |
|---|---|---|
| Section chunker | `citemed_ai/services/extractor/` (new sub-module) | Emits `(title, body, page_start, page_end, bbox_spans[])` |
| Chunk persistence | `lit_reviews/models/extractions.py` (new `ArticleSection` table) | FK to `AppraisalArticle`, vector column |
| KB ingest | New Django app `lit_reviews/knowledge_base/` | `KnowledgeDocument` + `KnowledgeChunk` tables, vector column |
| `find_in_paper` tool | Clio backend tool registry (under ECD-1652) | Returns chunks with anchor metadata |
| `consult_kb` tool | Clio backend tool registry | Filtered by KB type |
| `grade_this_article` tool | Composite — reads existing extraction fields + calls `consult_kb` | Cite-then-conclude pattern |
| pgvector | Already an MDP-213 peer-dependency; verify installed | Postgres extension |

**Frontend:**
- Extend `ClinicalAppraisalApp.vue` to host the Clio chat panel as a right-side tab/dock (reuse ECD-1619's panel component).
- New artifact type or inline-trigger: `paper_section_anchor` → on click, scrolls `PdfJsViewer.vue` to page + draws bbox overlay.
- KB-citation rendering: hover/click on a citation expands the source passage in-place.

**Conversation scoping:**
- Chat thread is paper-scoped (one thread per `AppraisalArticle`), so context = "this paper" implicitly, no need for the user to re-anchor every question.

**Reuse path:**
- WS transport: from ECD-1619.
- Tool-call streaming + artifact rendering: from ECD-1619.
- Agent loop: from ECD-1652 (whatever shape that lands on — Perceive / Plan / Classify / Act per the Clio manifesto).

## Acceptance Criteria

**Track 1:**
- A user on the clinical-appraisal page can ask "find the section on results" and Clio responds with a clickable trigger that scrolls + highlights the results section in the PDF.
- 5 sample questions across 3 sample papers return answers grounded in a chunk citation (page + bbox).
- An answer without a chunk citation is flagged in the UI as "ungrounded — verify before relying on."

**Track 2:**
- A user can ask "what would you GRADE this article as?" and Clio returns a GRADE classification with: (a) cited GRADE passages from KB, (b) references to the underlying AI-extracted fields it used.
- A user can ask "how should I extract the primary outcome measure?" for at least 3 pilot fields and get the SOP passage cited.
- KB-grounded answers visibly distinguish KB-citation from paper-citation.

## Estimate

**Discovery phase first (this is the recommended next step):**
- Spike — 8h: validate that ECD-1619's chat panel can be mounted on a non-search-flow page; verify pgvector is wired into citemed_web; pick the section-chunking strategy from the existing extractor output.
- Shape decision: 2h doc, building on MDP-220's Option A/B/C framing.

**If approved to build (rough — for budgeting, not commitment):**
- Track 1 backend (chunker + persist + embed + tool): ~24h
- Track 1 frontend (panel mount + bbox-scroll trigger): ~16h
- Track 2 backend (KB schema + ingest + 2 tools): ~20h
- Track 2 frontend (KB-citation rendering): ~8h
- Pilot KB content prep (GRADE + 3 SOPs): ~6h
- **Total: ~80h** if both tracks delivered together. Track 1 alone: ~40h.

Far over the playbook's 4h MVP target. Per playbook guidance: split into an **Epic + multiple child stories**, gated on the discovery spike.

**Critical path:** the architectural shape decision (same blocker as MDP-220). Without that, both tracks risk re-implementing infra Clio is going to own.

## Dependencies

- **ECD-1619** must reach Done — provides the chat-panel transport. Currently in QA so likely close.
- **ECD-1652** parent Clio epic's tool-registry pattern must be defined enough to add new tools without forking the agent loop.
- **pgvector** in the citemed_web Postgres. Verify in spike — MDP-213 assumes it but pilot deployment status unknown.
- **Section-quality from the extractor** — if `citemed_ai`'s current pipeline doesn't emit sections cleanly, chunking becomes a meaningful piece of work, not a freebie.
- **KB source documents** — somebody needs to drop GRADE PDFs / internal SOPs into the ingest pipeline. Non-engineering blocker.

## Open Questions

- **Q1: Shape (A/B/C, per MDP-220).** Separate agentic process / Clio loop / hybrid? Answer probably falls out of the ECD-1652 architecture once it lands.
- **Q2: Conversation scope.** Per-paper thread vs. per-user-across-papers? Per-paper is the user's stated mental model but worth validating.
- **Q3: Section quality.** Does the current extractor emit usable section structure, or do we need a separate sectionizer (e.g. GROBID-style)?
- **Q4: pgvector deployment.** Already in production Postgres or still a Strata-future dependency? Affects estimate non-trivially.
- **Q5: KB editorial authority.** Who curates the KB? Internal SOPs change — does ingest re-run nightly? On edit?
- **Q6: Confidence + ungrounded responses.** When Clio can't ground, does it refuse, hedge, or answer with a warning? User's framing strongly implies the first.
- **Q7: Relationship to Strata (MDP-213).** "Clio over Strata" is the long-term framing. Does this proposal deliberately *not* use the graph (because it doesn't exist yet) and revisit when Strata lands?
- **Q8: Sibling to ECD-1815 or under it?** Both are "Clio on a page surface" — file as sibling story under ECD-1652, or as a sibling epic alongside ECD-1815?

## Why This Matters

Two things compound here:
1. **Trust in AI extractions.** Today reviewers verify AI-extracted fields by cross-checking the PDF manually. Grounded chat — point at the bbox the answer came from — is the natural verification surface. The data model already stores `highlight_locations` for AI extractions; we'd be extending that grounding to free-text Q&A.
2. **Onboarding + training surface.** New clinical writers spend significant time learning the extraction rules and methodologies (GRADE, MEDDEV interpretations, internal SOPs). A KB-grounded Clio on the page they're already working on collapses that learning loop. The extractions page stops being just data-entry and becomes a teach-as-you-work surface.

Strategic positioning: this is the **per-paper** Clio surface, complementing ECD-1815's **per-artifact-document** Clio surface. Together they cover the two main analytical surfaces in the product (review-the-paper, write-the-document), both grounded, both KB-aware.
