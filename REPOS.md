# Sibling Repo Map

Orientation for cross-repo PM work. When a Jira ticket mentions a feature, use this to figure out where to grep.

All paths relative to `/Users/ethand320/code/citemed/`. Read access to all of these is allow-listed.

---

## Active product repos (most PM questions land here)

### `citemed_web/` — Evidence Cloud Platform
The main web product. Polyglot — Python (Django + Celery + Airflow), Vue/React frontends, Cypress for E2E.
- **Top-level surfaces:** `backend/`, `client_portal/`, `admin_side/`, `airflow/`, `accounts/`, `citesource/`, `configuration/`, `cypress/`, `deployment-infra/`
- **Has its own `CLAUDE.md`** at the repo root — read it for resource inventory.
- **Bitbucket pipeline:** `bitbucket-pipelines.yml` exists.
- **Most ECD-* tickets touch this repo.**

### `citemed_ai/` — CiteMed AI PDF Processing Engine
Medical PDF document parser + information extractor using LLMs. Python (Poetry/uv).
- **Top-level surfaces:** `citemed_ai/` (the package), `tests/`, `examples/`, `Testing Datasets/`, `test_data/`
- Includes `ai-89-*` workspaces (data-extraction trial outputs).
- No `CLAUDE.md` yet — orient by reading `README.md` + `SCREENING_README.md`.
- **AI-prefixed tickets / outcome-measure / screening work lives here.**

### `atlassian-trinity/` — Unified Atlassian CLI (dir name is `atlassian-trinity`)
The CLI you're already using (`trinity jira|confluence|bb ...`). JSON-first, agent-native.
- Source: `src/trinity/`
- Installed binary: `/opt/homebrew/bin/trinity`
- No `CLAUDE.md`.
- **When the user asks "can trinity do X?" the answer lives here** — `src/trinity/<area>/` per subcommand.

### `bitbucket-cli-for-claude-code/` — Standalone `bb` CLI
Older Bitbucket CLI. Trinity's `bb` subcommands largely supersede this for PM use, but the `bb` binary may still be invoked by some `scripts/core/*` files.

### `hubspot-openclaw/`
OpenClaw-compatible skill wrapping HubSpot CRM. Not a PM concern unless a ticket explicitly involves CRM data.

---

### `openclaw-hq/` — the agent fleet (at `~/code/openclaw-hq`, not under `citemed/`)
**Remington's own OpenClaw definition lives here**, at `agents/remington/`:
`CARD.md` · `BUILDOUT.md` · `workspace/` (SOUL/AGENTS/MEMORY/STATE, skills, tasks, cron)
· `mcp/` (trinity-mcp + pm-mcp over `pm_core`). It was moved out of this repo's
`openclaw/` dir on 2026-08-20 — see `ethandrower/remington` PR #14 for the history.
Deploy runbook: `openclaw-hq/deploy/remington-deploy.md`.

---

## Adjacent repos (less common, but referenced)

| Repo | What it is |
| --- | --- |
| `confluence-docs/` | Turns a Confluence space into a public support portal. |
| `endnote-migrator/` / `spartacus/` | EndNote → CiteSource bibliography migration library. (Same project, two names.) |
| `medical-search-polygot/` | Cross-database medical search query syntax validator. |
| `word_addon/` | MS Word Office Add-in (React + Fluent UI) for inserting citations. |
| `abstract_format/` | Abstract reformatting utility. |
| `exec-dashboard/` | Single-file HTML executive dashboard (capital burn rate / roadmap). |
| `citemed-challenge/` | Vue 3 + Django sandbox for the AI coding interview. |
| `evidence-maturity-model/` | (No README — investigate before referencing.) |
| `copywriting-deliverables/` | Marketing/copy assets. |

---

## Archive / inactive

`archive/`, `Claude Co-Work CRM Tasks/`, `construct/`, `scraper-tests/`, `product-project-manager-claude.zip`, `package-lock.json` (stray) — usually safe to ignore for PM work unless a ticket explicitly references them.

---

## Conventions to confirm

These are reasonable guesses based on filesystem signals — confirm before relying on them in escalations:

- **Jira project keys → repos:** `ECD-*` → `citemed_web` (matches `release-notes` workflow's `space = ECD`). `AI-*` likely → `citemed_ai` (based on `ai-89-*` workspace dirs). Other prefixes: unknown.
- **Branch naming:** memory notes `PROJ-XXX-description` as the default convention.

If a ticket key doesn't match either active repo, ask the user which repo it belongs to rather than guessing.

---

## Cross-repo grep cheats

```bash
# Find a ticket key referenced in code/branch names anywhere:
grep -rln "ECD-1234" /Users/ethand320/code/citemed/citemed_web /Users/ethand320/code/citemed/citemed_ai

# Recent commits touching a feature across both product repos:
for r in citemed_web citemed_ai; do
  echo "=== $r ==="; git -C /Users/ethand320/code/citemed/$r log --oneline -20 --all --grep="ECD-1234"
done

# Active branches on a remote:
git -C /Users/ethand320/code/citemed/citemed_web branch -a | grep ECD-1234
```
