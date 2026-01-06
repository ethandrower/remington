# Automated PR Review System

## Overview

Comprehensive PR review tracking database that monitors all pull requests, detects new commits, performs AI-powered code reviews using Claude, and can request changes directly in Bitbucket with developer tagging.

## Purpose

- **Track all PRs** across repositories with review status
- **Detect new commits** automatically to trigger re-reviews
- **Perform AI code reviews** using Claude for consistent quality checks
- **Post reviews to Bitbucket** with comments, inline suggestions, and change requests
- **Tag developers** in review comments for immediate notification
- **Maintain review history** for audit trail and metrics

## Database Schema

**Location**: `.claude/data/pr-reviews/pr_reviews.db` (SQLite)

### Table: pr_reviews

```sql
CREATE TABLE pr_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_title TEXT,
    pr_author TEXT,
    pr_author_bitbucket_username TEXT,
    pr_link TEXT,

    -- Commit tracking
    latest_commit_sha TEXT,
    last_reviewed_commit_sha TEXT,

    -- Review status
    review_status TEXT CHECK(review_status IN ('pending', 'reviewed', 'changes_requested', 'approved', 'declined')),
    needs_review BOOLEAN DEFAULT 1,

    -- Review metadata
    last_review_date TIMESTAMP,
    review_count INTEGER DEFAULT 0,
    reviewer TEXT DEFAULT 'CiteMed AI (Remington)',

    -- PR metadata
    pr_state TEXT, -- 'OPEN', 'MERGED', 'DECLINED'
    pr_created_at TIMESTAMP,
    pr_updated_at TIMESTAMP,
    files_changed INTEGER,
    lines_added INTEGER,
    lines_removed INTEGER,

    -- Tracking
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked_at TIMESTAMP,

    UNIQUE(repo, pr_number)
);
```

### Table: review_comments

```sql
CREATE TABLE review_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_review_id INTEGER REFERENCES pr_reviews(id),
    commit_sha TEXT,
    comment_type TEXT CHECK(comment_type IN ('general', 'file_specific', 'line_specific')),
    file_path TEXT,
    line_number INTEGER,
    comment_text TEXT,
    severity TEXT CHECK(severity IN ('info', 'suggestion', 'issue', 'critical')),
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bitbucket_comment_id TEXT
);
```

### Table: review_history

```sql
CREATE TABLE review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_review_id INTEGER REFERENCES pr_reviews(id),
    commit_sha TEXT,
    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    review_action TEXT CHECK(review_action IN ('approved', 'changes_requested', 'commented', 'declined')),
    summary TEXT,
    files_changed INTEGER,
    lines_added INTEGER,
    lines_removed INTEGER,
    issues_found INTEGER,
    critical_issues INTEGER
);
```

## Workflow

### Step 1: PR Discovery & Monitoring

```python
def monitor_prs():
    """Poll Bitbucket for new PRs and commit updates"""

    bb_api = BitbucketAPI(load_bb_config())
    workspace = "citemed"
    repos = ["citemed_web", "word_addon"]

    for repo in repos:
        # Get all open PRs from Bitbucket
        prs = bb_api.list_pull_requests(workspace, repo, state="OPEN")

        for pr in prs:
            pr_number = pr["id"]
            latest_commit = pr["source"]["commit"]["hash"]
            author = pr["author"]["display_name"]
            author_username = pr["author"]["username"]

            # Check if PR exists in database
            db_pr = db.get_pr(repo, pr_number)

            if not db_pr:
                # New PR detected
                db.create_pr_record(
                    repo=repo,
                    pr_number=pr_number,
                    pr_title=pr["title"],
                    pr_author=author,
                    pr_author_bitbucket_username=author_username,
                    pr_link=pr["links"]["html"]["href"],
                    latest_commit_sha=latest_commit,
                    pr_state=pr["state"],
                    pr_created_at=pr["created_on"],
                    pr_updated_at=pr["updated_on"],
                    needs_review=True
                )
                print(f"🆕 New PR detected: {repo}/PR-{pr_number}")

                # Trigger immediate review for new PRs
                perform_code_review(repo, pr_number)

            elif db_pr["latest_commit_sha"] != latest_commit:
                # New commit pushed - mark for re-review
                db.update_pr(
                    repo, pr_number,
                    latest_commit_sha=latest_commit,
                    needs_review=True,
                    pr_updated_at=pr["updated_on"]
                )
                print(f"📝 New commits pushed to {repo}/PR-{pr_number}")

                # Trigger re-review
                perform_code_review(repo, pr_number)

            else:
                # No changes, just update last_checked_at
                db.touch_pr(repo, pr_number)
```

### Step 2: Automated Code Review with Claude

```python
def perform_code_review(repo: str, pr_number: int):
    """Use Claude AI to review PR code changes"""

    print(f"\n🤖 Performing code review on {repo}/PR-{pr_number}...")

    bb_api = BitbucketAPI(load_bb_config())
    workspace = "citemed"

    # Get PR details
    pr = bb_api.get_pull_request(workspace, repo, pr_number)

    # Get code diff
    diff = bb_api.get_diff(workspace, repo, pr_number)

    # Get diffstat for context
    diffstat = bb_api.get_diffstat(workspace, repo, pr_number)
    files_changed = len(diffstat.get("values", []))
    lines_added = sum([f["lines_added"] for f in diffstat.get("values", [])])
    lines_removed = sum([f["lines_removed"] for f in diffstat.get("values", [])])

    # Build review prompt for Claude
    prompt = f"""You are performing a code review for Pull Request #{pr_number} in {repo}.

PR Title: {pr["title"]}
Author: {pr["author"]["display_name"]}
Description:
{pr.get("description", "No description provided")}

Files Changed: {files_changed}
Lines Added: {lines_added}
Lines Removed: {lines_removed}

CODE DIFF:
```diff
{diff[:50000] if len(diff) <= 50000 else diff[:50000] + "\\n[... diff truncated for length ...]"}
```

Perform a thorough code review focusing on:

1. **Code Quality**:
   - Logic errors or bugs
   - Performance issues (inefficient loops, N+1 queries, etc.)
   - Security vulnerabilities (SQL injection, XSS, authentication issues)
   - Code smells and anti-patterns

2. **Best Practices**:
   - Adherence to Python/JavaScript/Django/Vue.js standards
   - Proper error handling and edge cases
   - Test coverage (are tests included and adequate?)
   - Documentation (docstrings, comments for complex logic)

3. **Architecture & Design**:
   - Design patterns and SOLID principles
   - Separation of concerns
   - Maintainability and readability
   - Database design (indexes, relationships)

4. **Specific Issues to Check**:
   - Hardcoded values (use environment variables or config)
   - SQL injection risks
   - Missing null/undefined checks
   - Inefficient database queries
   - Memory leaks (especially in Vue.js)
   - Proper authentication/authorization checks

Provide your review in JSON format:
{{
  "overall_assessment": "approve" | "request_changes" | "comment",
  "severity": "low" | "medium" | "high" | "critical",
  "summary": "Brief 2-3 sentence overall summary of the changes and quality",
  "issues": [
    {{
      "type": "bug" | "performance" | "security" | "style" | "suggestion" | "architecture",
      "severity": "critical" | "major" | "minor" | "info",
      "file": "path/to/file.py",
      "line": 123,  // optional - include if you can identify specific line
      "description": "Detailed issue description explaining the problem",
      "suggestion": "Specific actionable fix or improvement"
    }}
  ],
  "positives": ["List 2-3 good things about this PR - well-tested, clean code, good patterns, etc."],
  "tests_included": true | false,
  "documentation_adequate": true | false,
  "estimated_review_time": "5 minutes" | "15 minutes" | "30 minutes" | "1 hour"
}}

IMPORTANT:
- Only include issues you're confident about
- Be constructive and specific
- Prioritize critical issues over style nitpicks
- Consider the context (is this a hotfix, new feature, refactor, etc.)
"""

    # Call Claude for review
    result = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--settings", ".claude/settings.local.json"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout for large PRs
    )

    if result.returncode == 0:
        try:
            # Parse Claude's JSON response
            output = result.stdout.strip()

            # Extract JSON (Claude might wrap in markdown)
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            elif "```" in output:
                json_start = output.find("```") + 3
                json_end = output.find("```", json_start)
                json_str = output[json_start:json_end].strip()
            else:
                json_str = output

            review_data = json.loads(json_str)

            # Post review to Bitbucket
            post_review_to_bitbucket(repo, pr_number, pr, review_data)

            # Update database
            db.update_review_record(
                repo, pr_number,
                review_status=review_data["overall_assessment"],
                needs_review=False,
                last_reviewed_commit_sha=pr["source"]["commit"]["hash"],
                last_review_date=datetime.now(),
                review_count=db.get_pr(repo, pr_number)["review_count"] + 1,
                files_changed=files_changed,
                lines_added=lines_added,
                lines_removed=lines_removed
            )

            # Save review history
            db.save_review_history(
                repo, pr_number,
                commit_sha=pr["source"]["commit"]["hash"],
                review_action=review_data["overall_assessment"],
                summary=review_data["summary"],
                files_changed=files_changed,
                lines_added=lines_added,
                lines_removed=lines_removed,
                issues_found=len(review_data["issues"]),
                critical_issues=len([i for i in review_data["issues"] if i["severity"] == "critical"])
            )

            print(f"✅ Review complete and posted to Bitbucket")
            return review_data

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse Claude's JSON response: {e}")
            print(f"Response preview: {result.stdout[:200]}...")
            return None

    else:
        print(f"❌ Claude review failed: {result.stderr}")
        return None
```

### Step 3: Post Review to Bitbucket

```python
def post_review_to_bitbucket(repo: str, pr_number: int, pr: dict, review_data: dict):
    """Post review comments to Bitbucket PR"""

    bb_api = BitbucketAPI(load_bb_config())
    workspace = "citemed"
    author_username = pr["author"]["username"]

    # Build main review comment with developer tag
    summary_comment = format_review_summary(review_data, author_username)

    # Post main comment
    main_comment_result = bb_api.add_comment(
        workspace,
        repo,
        pr_number,
        summary_comment
    )

    # Save main comment to database
    db.save_review_comment(
        repo, pr_number,
        commit_sha=pr["source"]["commit"]["hash"],
        comment_type="general",
        comment_text=summary_comment,
        severity=review_data["severity"],
        bitbucket_comment_id=main_comment_result.get("id")
    )

    # Post individual issue comments on specific lines (if line numbers provided)
    for issue in review_data["issues"]:
        if issue.get("line") and issue.get("file"):
            # Post inline comment
            inline_comment = f"**{issue['severity'].upper()} {issue['type'].upper()}**: {issue['description']}\\n\\n💡 **Suggestion**: {issue['suggestion']}"

            try:
                inline_result = bb_api.add_comment(
                    workspace,
                    repo,
                    pr_number,
                    inline_comment,
                    inline={
                        "path": issue["file"],
                        "to": issue["line"]
                    }
                )

                # Save inline comment to database
                db.save_review_comment(
                    repo, pr_number,
                    commit_sha=pr["source"]["commit"]["hash"],
                    comment_type="line_specific",
                    file_path=issue["file"],
                    line_number=issue["line"],
                    comment_text=inline_comment,
                    severity=issue["severity"],
                    bitbucket_comment_id=inline_result.get("id")
                )

            except Exception as e:
                print(f"⚠️  Failed to post inline comment: {e}")

    # Take action based on overall assessment
    if review_data["overall_assessment"] == "approve":
        try:
            bb_api.approve_pull_request(workspace, repo, pr_number)
            print(f"✅ Approved PR-{pr_number}")
        except Exception as e:
            print(f"⚠️  Failed to approve PR: {e}")

    elif review_data["overall_assessment"] == "request_changes":
        # Post a comment requesting changes (Bitbucket doesn't have explicit "request changes" like GitHub)
        try:
            changes_comment = f"@{author_username} - **Changes requested**. Please address the issues commented above before merging."
            bb_api.add_comment(workspace, repo, pr_number, changes_comment)
            print(f"🔄 Requested changes on PR-{pr_number}")
        except Exception as e:
            print(f"⚠️  Failed to request changes: {e}")


def format_review_summary(review_data: dict, developer_username: str) -> str:
    """Format review with developer tag"""

    assessment_emoji = {
        "approve": "✅",
        "request_changes": "🔄",
        "comment": "💬"
    }

    severity_emoji = {
        "critical": "🚨",
        "high": "⚠️",
        "medium": "⚡",
        "low": "ℹ️"
    }

    comment = f"""🤖 **Automated Code Review by CiteMed AI (Remington)**

@{developer_username} - Please review the feedback below:

---

**Overall Assessment**: {assessment_emoji.get(review_data['overall_assessment'], '')} {review_data['overall_assessment'].upper().replace('_', ' ')}
**Severity**: {severity_emoji.get(review_data['severity'], '')} {review_data['severity'].upper()}
**Estimated Review Time**: {review_data.get('estimated_review_time', 'N/A')}

**Summary**:
{review_data['summary']}

---

"""

    if review_data["issues"]:
        comment += f"### ⚠️ Issues Found ({len(review_data['issues'])})\n\n"

        # Group by severity
        critical = [i for i in review_data["issues"] if i["severity"] == "critical"]
        major = [i for i in review_data["issues"] if i["severity"] == "major"]
        minor = [i for i in review_data["issues"] if i["severity"] == "minor"]
        info = [i for i in review_data["issues"] if i["severity"] == "info"]

        for severity, issues, emoji in [
            ("CRITICAL", critical, "🚨"),
            ("MAJOR", major, "⚠️"),
            ("MINOR", minor, "⚡"),
            ("INFO", info, "ℹ️")
        ]:
            if issues:
                comment += f"\n**{emoji} {severity}**:\n\n"
                for issue in issues:
                    comment += f"**{issue['type'].upper()}** in `{issue['file']}`"
                    if issue.get("line"):
                        comment += f" (line {issue['line']})"
                    comment += f"\n_{issue['description']}_\n"
                    if issue.get("suggestion"):
                        comment += f"💡 **Suggestion**: {issue['suggestion']}\n"
                    comment += "\n"

    if review_data["positives"]:
        comment += f"\n### ✅ Positives\n\n"
        for positive in review_data["positives"]:
            comment += f"- {positive}\n"

    comment += f"\n---\n\n"
    comment += f"📝 **Tests Included**: {'✅ Yes' if review_data.get('tests_included') else '❌ No'}\n"
    comment += f"📖 **Documentation**: {'✅ Adequate' if review_data.get('documentation_adequate') else '⚠️ Needs improvement'}\n\n"
    comment += f"_This is an automated review. Human reviewers should still verify critical changes._\n"

    return comment
```

## Usage

### Command Line Interface

```bash
# Monitor PRs and perform reviews on new/updated PRs
python scripts/pr_review_bot.py monitor

# Review a specific PR manually
python scripts/pr_review_bot.py review citemed_web 92

# Show review status dashboard
python scripts/pr_review_bot.py status

# Show detailed review history for a PR
python scripts/pr_review_bot.py history citemed_web 92

# Re-review all open PRs that need review
python scripts/pr_review_bot.py review-all

# Export review metrics
python scripts/pr_review_bot.py metrics --output metrics.json
```

### Scheduled Automation

```bash
# Crontab entries

# Check for new PRs/commits every hour during business hours
0 9-17 * * 1-5 cd /path/to/project-manager && python scripts/pr_review_bot.py monitor

# Daily summary of review status posted to Slack
0 9 * * 1-5 cd /path/to/project-manager && python scripts/pr_review_bot.py status --post-to-slack
```

## Files to Create

- `scripts/pr_review_bot.py` - Main PR review automation script
- `.claude/data/pr-reviews/pr_reviews.db` - SQLite database (auto-created)
- `.claude/workflows/pr-review-automation.md` - This file (workflow documentation)
- `.claude/templates/pr-review-comment.md` - Review comment template

## Bitbucket API Methods Available

From `bitbucket-cli`:

- ✅ `list_pull_requests(workspace, repo, state="OPEN")` - Get all PRs
- ✅ `get_pull_request(workspace, repo, pr_id)` - Get PR details
- ✅ `get_diff(workspace, repo, pr_id)` - Get code changes
- ✅ `get_diffstat(workspace, repo, pr_id)` - Get files changed stats
- ✅ `add_comment(workspace, repo, pr_id, message, inline={...})` - Post comments
- ✅ `approve_pull_request(workspace, repo, pr_id)` - Approve PR
- ✅ `unapprove_pull_request(workspace, repo, pr_id)` - Remove approval
- ✅ `decline_pull_request(workspace, repo, pr_id, message)` - Decline PR
- ✅ `get_comments(workspace, repo, pr_id)` - See existing comments
- ✅ `get_activity(workspace, repo, pr_id)` - Get PR activity log

## Benefits

- 🤖 **Automated reviews** save developer time (5-30 min per PR)
- 🔍 **Consistent quality** checks across all PRs
- 📊 **Comprehensive tracking** of review status and history
- 🔄 **Automatic re-review** when new commits pushed
- 🏷️ **Developer tagging** for immediate notification
- 📈 **Review metrics** for team performance insights
- ⚡ **Fast feedback** - reviews within minutes of PR creation
- 🎯 **Specific suggestions** with file/line context
- 🔒 **Security checks** for common vulnerabilities
- 📚 **Knowledge base** builds over time from review history

## Safety Features

- Reviews are suggestions, not blockers (unless critical issues found)
- Human developers can override bot decisions
- Bot clearly identifies itself as automated review
- Severity levels help prioritize issues (critical vs info)
- Review history provides complete audit trail
- Dry-run mode for testing
- Can disable for specific PRs or file types

## Configuration

### Environment Variables

```bash
# Already configured via bitbucket-cli
BITBUCKET_WORKSPACE=citemed
BITBUCKET_REPO_TOKEN=<token>
```

### Settings

```python
# In scripts/pr_review_bot.py

# Repositories to monitor
MONITORED_REPOS = ["citemed_web", "word_addon"]

# Review triggers
REVIEW_ON_NEW_PR = True
REVIEW_ON_NEW_COMMIT = True
AUTO_APPROVE_MINOR_CHANGES = False  # Safety: keep False

# Review strictness
MIN_TEST_COVERAGE_WARNING = 0.7  # Warn if tests not included
REQUIRE_DOCUMENTATION = True

# Posting
POST_INLINE_COMMENTS = True  # Post on specific lines
POST_GENERAL_SUMMARY = True  # Always post overall summary
TAG_DEVELOPER = True  # @mention author in comments
```

## Metrics & Reporting

Track over time:
- PRs reviewed per day/week
- Average review time
- Issues found by severity
- Most common issue types
- PRs approved vs changes requested
- Review effectiveness (do issues get fixed?)
- Developer responsiveness to reviews

---

**Document Owner:** PM Agent Development
**Last Updated:** 2025-10-20
**Status:** Design Phase
**Priority:** HIGH
