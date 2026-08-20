#!/usr/bin/env bash
# Remington — Phase A safe prep (run ON oc-prod). NO fleet impact:
# touches only ~/code/citemed/{project-manager,atlassian-trinity} and
# ~/.openclaw/workspace-pm. Does NOT edit openclaw.json or restart the service.
set -euo pipefail

BRANCH="${1:-worktree-remington-routines}"   # switch to 'main' once PR #14 is merged
CODE=~/code/citemed
PM="$CODE/project-manager"
TRINITY="$CODE/atlassian-trinity"
VENV="$PM/.venv-remington"
WS=~/.openclaw/workspace-pm

echo "== 1. clone/update repos =="
mkdir -p "$CODE"
if [ -d "$PM/.git" ]; then git -C "$PM" fetch --quiet origin; else git clone --quiet git@github.com:ethandrower/remington.git "$PM"; fi
git -C "$PM" checkout --quiet "$BRANCH"
git -C "$PM" pull --quiet --ff-only origin "$BRANCH" || true
if [ -d "$TRINITY/.git" ]; then git -C "$TRINITY" pull --quiet --ff-only; else git clone --quiet git@github.com:ethandrower/atlassian-trinity.git "$TRINITY"; fi

echo "== 2. build MCP venv =="
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$PM/openclaw/remington_mcp/requirements.txt"
"$VENV/bin/pip" install --quiet -e "$TRINITY"

echo "== 3. import-test the MCP servers (no creds needed to import) =="
( cd "$PM/openclaw" && "$VENV/bin/python" -c "
import mcp
import remington_mcp.trinity_mcp as t
import remington_mcp.pm_mcp as p
print('OK: mcp', getattr(mcp,'__version__','?'), '| trinity_mcp + pm_mcp import clean')
" )

echo "== 4. stage workspace-pm (rsync; preserve runtime STATE.md + memory/) =="
mkdir -p "$WS"
rsync -az --delete \
  --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.venv-remington' \
  --filter='protect STATE.md' --filter='protect memory/***' \
  "$PM/openclaw/" "$WS/"

echo "== DONE (Phase A). Next: Phase B/C in DEPLOY.md (gated on secrets). =="
