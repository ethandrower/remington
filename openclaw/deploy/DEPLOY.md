# Deploying Remington to oc-prod

Gateway: `ethand320@100.112.73.91` (Tailscale). Service: `openclaw-gateway.service`
(systemd user unit). Config: `~/.openclaw/openclaw.json` (keep a `.bak` before every edit).
Piper/Tess/Sergei are **live on this host** — every config edit + restart affects them, so
back up and be surgical.

## Phases

### Phase A — safe prep (no fleet impact) → `deploy.sh`
Clones code, builds the MCP venv, import-tests the servers, and stages the workspace.
Touches only new paths (`~/code/citemed/{project-manager,atlassian-trinity}`,
`~/.openclaw/workspace-pm`). Does **not** edit `openclaw.json` or restart anything.

```bash
ssh ethand320@100.112.73.91 'bash -s' < deploy.sh          # or run on the box
```

### Phase B — register (fleet-affecting; needs secrets) — MANUAL, gated
1. **Back up:** `cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak-remington-$(date +%Y%m%d)`
2. Merge the fragments from `agent-config.json` into `openclaw.json`:
   - append the `pm` agent to `agents.list`
   - add `trinity` + `pm` under `mcp.servers` (fill the `env` tokens from the secret store)
   - add the `remington` Slack account under `channels.slack.accounts` (needs the Slack app — see below)
   - append the `pm`→`remington` `binding`
3. **Restart:** `systemctl --user restart openclaw-gateway.service` and check `journalctl --user -u openclaw-gateway -n 50`.
4. Smoke-test: DM Remington in Slack, and manually run one cron job (see Phase D).

### Phase C — cron
Merge `../cron/jobs.json` into `~/.openclaw/cron/jobs.json` (back up first). Jobs ship
`enabled:false`. Before enabling each: fill the real Slack channel ID into `delivery.to`
and the job `message`. Enable **one** (start with `sla-sweep` or `standup`), watch a run,
then enable the rest.

### Phase D — verify a single run
Trigger one job's message as a manual agent turn (or wait for its cron). Confirm: tools
authenticate (no `{"error":...,"type":"auth"}`), STATE.md is read + written, and the digest
posts to the right channel. Then widen.

## What still needs YOU (human-only)

| Item | Why | Blocks |
|---|---|---|
| **Slack app for Remington** (bot `xoxb-` + app `xapp-` tokens) | each fleet agent has its own Slack app; Remington needs one, invited to his 8 channels | all Slack posting + reflexes |
| **Slack channel IDs** | cron `delivery.to` + task messages need real `C...` IDs; some channels may not exist yet | enabling any cron job |
| **Atlassian API token in gateway env** | trinity headless auth (`ATLASSIAN_EMAIL`/`ATLASSIAN_API_TOKEN`) for `pm`+`trinity` MCP | every routine (else auth errors) |
| **Bitbucket app password** | PR SLA / review tools | PR-related routines only |
| **Jira/Bitbucket/Confluence webhooks → gateway** | reflexes (comment/PR/page @mentions) replace the old pollers; needs Atlassian-admin config + the gateway's reachable hook URL | ⚡ reflexes only (cron routines work without them) |

Everything else (workspace, skills, tasks, MCP code, cron definitions, agent/config
fragments) is built and staged by this repo + `deploy.sh`.

## Rollback
Restore `openclaw.json` from the `.bak`, remove the `workspace-pm`/cron additions, restart.
The `pm` agent is additive — removing its `agents.list` entry + binding fully de-registers it.
