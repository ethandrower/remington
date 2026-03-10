"""
Fetch PR #246 details, diff, and diffstat from Bitbucket.
Loads .env credentials before importing from src.tools.base.
"""

import json
import os
import sys

# Add project root to path so src imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Load .env manually first so env vars are set before any imports
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import requests
from src.tools.base import get_bitbucket_auth_headers

WORKSPACE = "citemed"
REPO_SLUG = "citemed_web"
PR_NUMBER = 246

BASE_PR_URL = f"https://api.bitbucket.org/2.0/repositories/{WORKSPACE}/{REPO_SLUG}/pullrequests/{PR_NUMBER}"


def fetch_json(url, headers):
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def fetch_text(url, headers):
    text_headers = {k: v for k, v in headers.items() if k != "Accept"}
    response = requests.get(url, headers=text_headers)
    response.raise_for_status()
    return response.text


def main():
    print("Fetching Bitbucket auth headers...")
    headers = get_bitbucket_auth_headers()

    print(f"Fetching PR #{PR_NUMBER} details from {BASE_PR_URL} ...")
    pr_details = fetch_json(BASE_PR_URL, headers)

    details_path = os.path.join(PROJECT_ROOT, "pr246_details.json")
    with open(details_path, "w") as f:
        json.dump(pr_details, f, indent=2)
    print(f"  Saved PR details to {details_path}")

    links = pr_details.get("links", {})
    diff_url = links.get("diff", {}).get("href") or f"{BASE_PR_URL}/diff"
    diffstat_url = links.get("diffstat", {}).get("href") or f"{BASE_PR_URL}/diffstat"

    print(f"  Diff URL:     {diff_url}")
    print(f"  Diffstat URL: {diffstat_url}")

    print("Fetching full diff...")
    diff_text = fetch_text(diff_url, headers)
    diff_path = os.path.join(PROJECT_ROOT, "pr246_full_diff.txt")
    with open(diff_path, "w") as f:
        f.write(diff_text)
    print(f"  Saved diff to {diff_path} ({len(diff_text):,} chars)")

    print("Fetching diffstat...")
    all_values = []
    next_url = diffstat_url
    while next_url:
        page = fetch_json(next_url, headers)
        all_values.extend(page.get("values", []))
        next_url = page.get("next")

    diffstat_data = {"values": all_values}
    diffstat_path = os.path.join(PROJECT_ROOT, "pr246_diffstat.json")
    with open(diffstat_path, "w") as f:
        json.dump(diffstat_data, f, indent=2)
    print(f"  Saved diffstat to {diffstat_path}")

    print()
    print("=" * 70)
    print("PR #246 SUMMARY")
    print("=" * 70)
    print(f"Title  : {pr_details.get("title", "N/A")}")
    print(f"State  : {pr_details.get("state", "N/A")}")
    author = pr_details.get("author", {}).get("display_name", "N/A")
    print(f"Author : {author}")
    source_branch = pr_details.get("source", {}).get("branch", {}).get("name", "N/A")
    dest_branch = pr_details.get("destination", {}).get("branch", {}).get("name", "N/A")
    print(f"Branch : {source_branch} -> {dest_branch}")
    print(f"Created: {pr_details.get("created_on", "N/A")}")
    print(f"Updated: {pr_details.get("updated_on", "N/A")}")

    print(f"
Files Changed ({len(all_values)} files):")
    total_added = 0
    total_removed = 0
    for entry in all_values:
        added = entry.get("lines_added", 0)
        removed = entry.get("lines_removed", 0)
        total_added += added
        total_removed += removed
        file_path = entry.get("new", {}).get("path") or entry.get("old", {}).get("path", "unknown")
        status = entry.get("status", "")
        print(f"  [{status:8s}] +{added:<5} -{removed:<5} {file_path}")

    print(f"
Totals: +{total_added} lines added, -{total_removed} lines removed")

    print("
First 100 lines of diff:")
    print("-" * 70)
    diff_lines = diff_text.splitlines()
    for i, line in enumerate(diff_lines[:100], 1):
        print(f"{i:4d}  {line}")
    if len(diff_lines) > 100:
        print(f"  ... ({len(diff_lines) - 100} more lines)")

    print("
Done.")


if __name__ == "__main__":
    main()
