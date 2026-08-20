#!/usr/bin/env python3
"""
Board Hygiene Tool - detect Jira board decay

Finds the decay patterns that plain JQL cannot express on its own. Reports
candidates with evidence; it never mutates anything. See
.claude/skills/board-hygiene/SKILL.md for what each pattern means and the
verification discipline that must follow.

Sweeps:
    orphans   Epics with no parent at all
    empty     Initiatives with no children
    stranded  Open work whose parent is Complete/Declined (no single JQL exists)
    phantoms  Issue keys cited in descriptions that do not resolve
    stale     Items parked in a review state past a threshold
    all       Every sweep above

Usage:
    python -m src.tools.jira.board_hygiene all
    python -m src.tools.jira.board_hygiene stranded --project ECD
    python -m src.tools.jira.board_hygiene stale --days 21
    python -m src.tools.jira.board_hygiene all --json
"""

import argparse
import json
import re
import sys
from typing import Optional

from .search import search_jira

# Statuses that mean "someone is supposedly on this". A ticket sitting here
# untouched for weeks is the shipped-but-never-closed pattern more often than not.
REVIEW_STATES = [
    "Pending Approval",
    "Changes Requested",
    "QA",
    "Blocked",
    "In Refinement",
]

DONE_STATUSES = {"Complete", "Declined"}

ISSUE_KEY_RE = re.compile(r"\b((?:ECD|AI|MDP|IN)-\d{1,6})\b")


def _issues(jql: str, max_results: int = 200, fields: Optional[list] = None) -> list:
    """Run a JQL search and return the issue list, tolerating tool shape drift."""
    try:
        res = search_jira(jql, max_results=max_results, fields=fields)
    except Exception as exc:  # a failed sweep must not kill the others
        print(f"  ! query failed: {exc}", file=sys.stderr)
        return []
    if isinstance(res, dict):
        return res.get("issues", [])
    return res or []


def _field(issue: dict, name: str):
    """Issues come back either flattened or nested under 'fields'."""
    if name in issue:
        return issue[name]
    return (issue.get("fields") or {}).get(name)


def _status(issue: dict) -> str:
    s = _field(issue, "status")
    if isinstance(s, dict):
        return s.get("name") or ""
    return s or ""


def _parent_key(issue: dict) -> Optional[str]:
    for key in ("epic_key", "parent_key"):
        v = _field(issue, key)
        if v:
            return v
    p = _field(issue, "parent")
    if isinstance(p, dict):
        return p.get("key")
    return p


def find_orphan_epics(project: str) -> list:
    """Epics with no parent — invisible to every initiative view and to Plans."""
    return _issues(
        f"project = {project} AND type = Epic AND parent IS EMPTY "
        f"AND statusCategory != Done ORDER BY updated ASC"
    )


def find_empty_initiatives(project: str) -> list:
    """Initiatives with nothing under them: finished, or never started."""
    inits = _issues(
        f"project = {project} AND type = Initiative AND statusCategory != Done"
    )
    if not inits:
        return []
    keys = [i.get("key") for i in inits if i.get("key")]
    have = set()
    for n in range(0, len(keys), 50):
        chunk = ",".join(keys[n : n + 50])
        for kid in _issues(f"parent in ({chunk})", max_results=400):
            pk = _parent_key(kid)
            if pk:
                have.add(pk)
    return [i for i in inits if i.get("key") not in have]


def find_stranded(project: str) -> list:
    """
    Open work under a Complete/Declined parent.

    There is no JQL for this: collect every open issue's parent, look those
    parents up, and keep the children whose parent is closed. This is the
    pattern that hides active-sprint work, so it is worth the extra queries.
    """
    kids = _issues(
        f"project in ({project}) AND statusCategory != Done AND parent IS NOT EMPTY",
        max_results=400,
    )
    parents = sorted({_parent_key(k) for k in kids if _parent_key(k)})
    dead = {}
    for n in range(0, len(parents), 50):
        chunk = ",".join(parents[n : n + 50])
        for p in _issues(f"key in ({chunk})", max_results=120):
            if _status(p) in DONE_STATUSES:
                dead[p.get("key")] = _status(p)
    out = []
    for k in kids:
        pk = _parent_key(k)
        if pk in dead:
            k = dict(k)
            k["_dead_parent"] = pk
            k["_dead_parent_status"] = dead[pk]
            out.append(k)
    return out


def find_phantom_keys(project: str) -> list:
    """
    Issue keys cited in initiative/epic descriptions that do not resolve.

    Jira never validates keys written inside description text, so definition-of-done
    lists quietly accumulate keys that were never created or were renumbered.
    """
    parents = _issues(
        f"project = {project} AND type in (Initiative, Epic) AND statusCategory != Done",
        max_results=200,
        fields=["summary", "description", "status"],
    )
    cited = {}
    for p in parents:
        desc = _field(p, "description") or ""
        if not isinstance(desc, str):
            continue
        for key in set(ISSUE_KEY_RE.findall(desc)):
            if key != p.get("key"):
                cited.setdefault(key, []).append(p.get("key"))
    if not cited:
        return []
    keys = sorted(cited)
    resolved = set()
    for n in range(0, len(keys), 50):
        chunk = ",".join(keys[n : n + 50])
        for i in _issues(f"key in ({chunk})", max_results=120):
            resolved.add(i.get("key"))
    return [
        {"key": k, "cited_by": cited[k]} for k in keys if k not in resolved
    ]


def find_stale_review(project: str, days: int = 14) -> list:
    """Items parked in a review state — the shipped-but-never-closed candidates."""
    states = ", ".join(f'"{s}"' for s in REVIEW_STATES)
    return _issues(
        f"project = {project} AND statusCategory != Done AND status in ({states}) "
        f"AND updated <= -{days}d ORDER BY updated ASC",
        max_results=200,
    )


def _print(title: str, rows: list, render) -> None:
    print(f"\n=== {title}: {len(rows)} ===")
    for r in rows:
        print("  " + render(r))


def main() -> int:
    ap = argparse.ArgumentParser(description="Detect Jira board decay (read-only)")
    ap.add_argument(
        "sweep",
        nargs="?",
        default="all",
        choices=["all", "orphans", "empty", "stranded", "phantoms", "stale"],
    )
    ap.add_argument("--project", default="ECD")
    ap.add_argument("--days", type=int, default=14, help="staleness threshold")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    want = (
        {"orphans", "empty", "stranded", "phantoms", "stale"}
        if args.sweep == "all"
        else {args.sweep}
    )
    out = {}

    if "orphans" in want:
        out["orphan_epics"] = find_orphan_epics(args.project)
    if "empty" in want:
        out["empty_initiatives"] = find_empty_initiatives(args.project)
    if "stranded" in want:
        out["stranded"] = find_stranded(args.project)
    if "phantoms" in want:
        out["phantom_keys"] = find_phantom_keys(args.project)
    if "stale" in want:
        out["stale_review"] = find_stale_review(args.project, args.days)

    if args.as_json:
        print(json.dumps(out, indent=2, default=str))
        return 0

    def base(i):
        return f"{i.get('key'):10} {_status(i):20} {str(_field(i, 'summary'))[:56]}"

    if "orphan_epics" in out:
        _print("Epics with no parent", out["orphan_epics"], base)
    if "empty_initiatives" in out:
        _print("Initiatives with no children", out["empty_initiatives"], base)
    if "stranded" in out:
        _print(
            "Open work under a Complete/Declined parent",
            out["stranded"],
            lambda i: f"{base(i)}  <- {i['_dead_parent']} [{i['_dead_parent_status']}]",
        )
    if "phantom_keys" in out:
        _print(
            "Phantom keys cited in descriptions",
            out["phantom_keys"],
            lambda r: f"{r['key']:10} cited by {', '.join(r['cited_by'])}",
        )
    if "stale_review" in out:
        _print(
            f"Parked in a review state >{args.days}d",
            out["stale_review"],
            base,
        )

    print(
        "\nThese are candidates, not conclusions. Before acting, verify each against "
        "the code on develop, and confirm any write with a direct issue fetch rather "
        "than search — the index lags. See .claude/skills/board-hygiene/SKILL.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
