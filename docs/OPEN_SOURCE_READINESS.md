# Open Source Readiness Assessment

**Status**: 🔴 Not Ready - Requires Significant Refactoring
**Date**: 2026-01-05
**Scope**: Prepare project-manager for public release on GitHub

---

## Executive Summary

This project contains significant amounts of **CiteMed-specific** content that must be generalized before public release. The codebase references:
- **44 files** with hardcoded CloudId `67bbfd03-b309-414f-9640-908213f80628`
- **49 files** with hardcoded Jira instance `citemed.atlassian.net`
- **52 files** with team member names (Mohamed, Ahmed, Thanh, Valentin, Josh)
- **158 files** with "CiteMed", "Evidence Cloud Development", or "ECD" project references
- **84 files** mentioning API keys, tokens, secrets, and credentials

---

## Priority 1: Security & Credentials (BLOCKER)

### Hardcoded Secrets - IMMEDIATE ACTION REQUIRED

#### CloudId References (44 files)
**Current**: `67bbfd03-b309-414f-9640-908213f80628` hardcoded throughout
**Required**: Move to environment variable `ATLASSIAN_CLOUD_ID`

**Files to update**:
```
.claude/CLAUDE.md - Line 88
.env.example - Line 31 (already exists, keep as example)
src/orchestration/claude_code_orchestrator.py
docs/CONFIGURATION.md
README.md
tests/test_jira_tools.py
src/tools/base.py
scripts/core/standup_workflow.py
scripts/core/jira_api_client.py
scripts/utilities/sync_team_from_confluence.py
[... and 34 more files]
```

**Action**: Create a utility function that reads from environment:
```python
# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

def get_cloud_id():
    cloud_id = os.getenv('ATLASSIAN_CLOUD_ID')
    if not cloud_id:
        raise ValueError("ATLASSIAN_CLOUD_ID environment variable not set")
    return cloud_id
```

Replace all hardcoded instances with:
```python
from src.config import get_cloud_id
cloud_id = get_cloud_id()
```

#### Jira Instance URL References (49 files)
**Current**: `citemed.atlassian.net` hardcoded
**Required**: Move to environment variable `JIRA_INSTANCE_URL`

**Update `.env.example`**:
```bash
# Jira Instance Configuration
JIRA_INSTANCE_URL=https://your-company.atlassian.net
```

#### API Token References (84 files)
**Status**: ✅ Most are in documentation/comments explaining how to get tokens
**Action**: Audit to ensure no actual tokens are committed

---

## Priority 2: Company-Specific References

### Project Key "ECD" (Evidence Cloud Development)
**Impact**: 158 files
**Current**: Hardcoded `ECD` throughout codebase
**Required**: Move to environment variable `JIRA_PROJECT_KEY`

**Already in `.env.example`**:
```bash
ATLASSIAN_PROJECT_KEY=ECD  # Change to YOUR_PROJECT_KEY
```

**Files requiring updates**:
```
.claude/CLAUDE.md - Multiple references
README.md - Overview sections
All agent files in .claude/agents/
All workflow files in .claude/workflows/
Test files with example JQL queries
```

**Action**:
1. Update documentation to use generic `YOUR_PROJECT` placeholders
2. Update code to read from `os.getenv('JIRA_PROJECT_KEY')`
3. Update example JQL queries to use `project = ${PROJECT_KEY}` syntax

### Team Member Names (52 files)
**Current**: Hardcoded names (Mohamed, Ahmed, Thanh, Valentin, Josh)
**Required**: Generic references or configurable team roster

**Files**:
```
.claude/CLAUDE.md - Lines 92-97
tests/conftest.py - Test fixtures
docs/testing/INTERACTIVE_TEST_GUIDE.md
All example Slack messages
All example Jira comments
Workflow documentation examples
```

**Action**:
1. Replace with generic examples: `Developer 1`, `Developer 2`, `@john.doe`, `@jane.smith`
2. Remove hardcoded team roster from `.claude/CLAUDE.md`
3. Make team roster configurable via:
   - Confluence page sync (current implementation)
   - OR `.env` variables
   - OR `team_config.json` file

**Update `.claude/CLAUDE.md`**:
```markdown
### Team Members

Team members are automatically synced from Confluence or configured via environment variables.

**To configure team roster:**
1. Set `CONFLUENCE_TEAM_PAGE_ID` in `.env` to sync from Confluence
2. OR manually define in `.env`:
   ```
   TEAM_MEMBER_1=John Doe
   TEAM_MEMBER_2=Jane Smith
   ```
```

### Company Name "CiteMed" (158 files)
**Impact**: Everywhere
**Required**: Generic naming or configurable

**Files**:
```
README.md - Title, descriptions
.claude/CLAUDE.md - Title, purpose statement
All documentation headers
Package.json - Project name
requirements.txt comments
```

**Action**:
1. **Repository Name**: Keep as `project-manager` (already generic)
2. **Documentation**: Replace with generic descriptions:
   - ❌ "CiteMed Project Manager - Autonomous Agent"
   - ✅ "Autonomous Project Management Agent for Jira/Slack/Bitbucket"
3. **Purpose Statements**: Remove company-specific context
4. **Add configuration**: `COMPANY_NAME` environment variable for Slack messages

**Example Update for `README.md`**:
```markdown
# Autonomous Project Management Agent

An AI-powered project management assistant that monitors Jira, Bitbucket, and Slack for team activity, providing intelligent responses, automated code reviews, and SLA compliance tracking.

Originally built for managing agile software development teams, this agent automates:
- Daily standup report generation
- SLA compliance monitoring
- Automated PR code reviews
- Sprint health analysis
- Team productivity tracking
```

---

## Priority 3: Repository Path References

### Absolute Path References
**Current**: `/Users/ethand320/code/citemed/*` hardcoded
**Required**: Relative paths or environment variables

**Files**:
```
.env.example - Lines 66-68:
  CITEMED_WEB_PATH=/Users/ethand320/code/citemed/citemed_web
  WORD_ADDON_PATH=/Users/ethand320/code/citemed/word_addon
  PM_AGENT_PATH=/Users/ethand320/code/citemed/project-manager
```

**Action**:
1. Update `.env.example` with generic placeholders:
```bash
# Repository Paths (absolute paths to codebases you want to monitor)
# These are optional - only needed for multi-repo code analysis
MAIN_REPO_PATH=/path/to/your/main/repository
SECONDARY_REPO_PATH=/path/to/secondary/repository  # Optional
PM_AGENT_PATH=/path/to/project-manager  # This repository
```

2. Update documentation to explain multi-repo monitoring is optional
3. Provide single-repo quickstart as default

---

## Priority 4: Documentation Overhaul

### Files Requiring Genericization

#### `.claude/CLAUDE.md` (Primary Agent Instructions)
**Current**: CiteMed-specific instructions throughout
**Required Changes**:
- [ ] Remove CloudId (line 88)
- [ ] Remove Jira instance (line 89)
- [ ] Remove project key "ECD" (line 90)
- [ ] Remove team member names (lines 92-97)
- [ ] Update "Relationship to CiteMed Codebase" section (lines 6-24)
- [ ] Genericize all example JQL queries
- [ ] Update Slack channel references

**New Structure**:
```markdown
## Configuration

### Atlassian Setup
Configure your Atlassian environment in `.env`:
- `ATLASSIAN_CLOUD_ID` - Your Atlassian Cloud ID
- `JIRA_INSTANCE_URL` - Your Jira instance URL
- `JIRA_PROJECT_KEY` - Your primary project key

### Team Configuration
[Instructions for setting up team roster]

### Repository Monitoring
[Instructions for multi-repo setup - OPTIONAL]
```

#### `README.md`
**Required Changes**:
- [ ] Update title to be generic
- [ ] Remove CiteMed references in overview
- [ ] Add "Getting Started" quickstart for new users
- [ ] Add "Configuration" section explaining all environment variables
- [ ] Update examples to use generic project names
- [ ] Add "Multi-Repo Monitoring" as advanced feature

#### All Documentation Files
**Pattern to find/replace**:
```bash
# Find all CiteMed references
rg -i "citemed" --type md

# Find all ECD references (but be careful - might be in code comments)
rg "ECD-[0-9]" --type md
rg '"ECD"'
```

**Action**:
- Replace company-specific examples with generic ones
- Use placeholders like `YOUR_COMPANY`, `YOUR_PROJECT`, `PROJ-123`

---

## Priority 5: Testing & Examples

### Test Fixtures (tests/conftest.py)
**Current**: Uses CiteMed team names and project keys
**Action**:
```python
# Replace specific names with generic ones
@pytest.fixture
def sample_jira_issue_context():
    return {
        "issue_key": "PROJ-123",  # Was ECD-862
        "summary": "Implement user authentication",
        "assignee": "Developer A",  # Was Mohamed
        "comments": [
            {
                "author": "Manager",  # Was Ethan
                "text": "What's the status?",
            }
        ]
    }
```

### Example Workflows
**Files**:
```
.claude/workflows/*.md
docs/testing/INTERACTIVE_TEST_GUIDE.md
```

**Action**: Replace all examples with generic team/project names

---

## Priority 6: Configuration Files

### `.env.example` - Already Excellent!
**Status**: ✅ Mostly ready
**Minor Updates Needed**:

```bash
# Update line 31
ATLASSIAN_CLOUD_ID=your-cloud-id-here  # Remove actual ID

# Update line 32
ATLASSIAN_PROJECT_KEY=YOUR_PROJECT  # Make it clear this is a placeholder

# Add new section
# ============================================================================
# COMPANY CONFIGURATION
# ============================================================================
COMPANY_NAME=YourCompany  # Used in Slack messages and reports
```

### `.mcp.json.example`
**Status**: ✅ Exists and is generic
**Action**: No changes needed

---

## Priority 7: Legal & Licensing

### Add LICENSE File
**Required**: Choose an open-source license
**Recommendations**:
- **MIT License** - Most permissive, good for commercial use
- **Apache 2.0** - Includes patent grant, enterprise-friendly
- **GPL v3** - Copyleft, requires derivatives to be open source

**Action**: Create `LICENSE` file with chosen license

### Add CONTRIBUTING.md
**Required**: Guide for external contributors
**Contents**:
```markdown
# Contributing to Project Manager Agent

## Getting Started
[Setup instructions]

## Development Workflow
[Branch naming, commit messages, PR process]

## Code Style
[Python style guide, linting, formatting]

## Testing
[How to run tests, coverage requirements]

## Documentation
[How to update docs]

## Submitting PRs
[PR checklist, review process]
```

---

## Priority 8: Heroku Deployment Configs

### `deployment/heroku/app.json`
**Current**: Contains CiteMed-specific environment variables
**Action**: Update with generic defaults and clear documentation

### `Procfile`
**Status**: ✅ Generic
**Action**: No changes needed

---

## Priority 9: Git History Sanitization

### Check for Committed Secrets
**Action**:
```bash
# Search git history for potential secrets
git log -S "ATLASSIAN_API_TOKEN" --all
git log -S "SLACK_BOT_TOKEN" --all
git log -S "sk-ant-" --all  # Anthropic API keys

# Check for .env commits
git log --all --full-history -- .env
```

**If secrets found**:
1. ⚠️ **CRITICAL**: Revoke all exposed tokens/keys immediately
2. Use `git-filter-repo` or `BFG Repo-Cleaner` to remove from history
3. Force push to clean repository
4. **OR** Start fresh repository with current clean code

---

## Implementation Checklist

### Phase 1: Security (Week 1) - BLOCKER
- [ ] Audit git history for secrets
- [ ] Create `src/config.py` with environment variable loader
- [ ] Replace all hardcoded CloudIds with `get_cloud_id()`
- [ ] Replace all hardcoded Jira URLs with `get_jira_url()`
- [ ] Update `.env.example` to remove real CloudId
- [ ] Test all workflows with environment variables

### Phase 2: Documentation (Week 1-2)
- [ ] Update `.claude/CLAUDE.md` to be generic
- [ ] Rewrite `README.md` for public audience
- [ ] Update all workflow documentation examples
- [ ] Update test fixtures to use generic names
- [ ] Create `CONTRIBUTING.md`
- [ ] Add `LICENSE` file

### Phase 3: Code Refactoring (Week 2)
- [ ] Replace hardcoded project key with environment variable
- [ ] Make team roster configurable (not hardcoded)
- [ ] Update all test files to use generic data
- [ ] Remove absolute path dependencies

### Phase 4: Polish (Week 3)
- [ ] Add quickstart guide for new users
- [ ] Create demo video or GIF
- [ ] Add badges to README (build status, license, etc.)
- [ ] Set up GitHub Issues templates
- [ ] Create GitHub Actions for CI/CD

### Phase 5: Pre-Release (Week 3-4)
- [ ] Full end-to-end testing with clean `.env`
- [ ] Security audit
- [ ] Documentation review
- [ ] Prepare announcement blog post
- [ ] Create initial GitHub release

---

## Risk Assessment

### High Risk
- **Exposed secrets in git history** - Could compromise CiteMed production systems
  - **Mitigation**: History rewrite or fresh repository

### Medium Risk
- **Hardcoded configurations breaking for other users** - Poor first-time experience
  - **Mitigation**: Comprehensive `.env.example` and error messages

### Low Risk
- **Documentation still referencing CiteMed in edge cases** - Confusing but not breaking
  - **Mitigation**: Thorough grep/replace, community PR corrections

---

## Estimated Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Security Cleanup | 8-16 hours | 🔴 Critical |
| Documentation Overhaul | 16-24 hours | 🟡 High |
| Code Refactoring | 12-20 hours | 🟡 High |
| Testing & Validation | 8-12 hours | 🟢 Medium |
| Polish & Release Prep | 4-8 hours | 🟢 Medium |
| **TOTAL** | **48-80 hours** | **~2 weeks** |

---

## Recommended Approach

### Option A: In-Place Refactoring (Recommended)
**Pros**:
- Preserves git history and context
- Can do incrementally
- Easy to test changes

**Cons**:
- Requires careful history sanitization
- Risk of missing hardcoded values

**Steps**:
1. Create feature branch `open-source-prep`
2. Implement Phase 1-4 changes incrementally
3. Use `git-filter-repo` to clean history if needed
4. Create new public repository with cleaned history
5. Push cleaned code to public GitHub

### Option B: Fresh Repository
**Pros**:
- Clean slate, no history concerns
- Guaranteed no secrets
- Forces review of all code

**Cons**:
- Loses development history
- More work to set up fresh

**Steps**:
1. Create new repository `ai-project-manager`
2. Copy only source files (not .git)
3. Manually refactor as you copy
4. Fresh git init
5. Public from day one

---

## Post-Release Maintenance

### Community Engagement
- [ ] Monitor GitHub Issues daily
- [ ] Label issues as bug/feature/question
- [ ] Respond to PRs within 48 hours
- [ ] Monthly release cycle

### Documentation Updates
- [ ] Keep README.md updated with new features
- [ ] Add troubleshooting FAQ
- [ ] Create video tutorials

### Feature Roadmap
- [ ] Public roadmap in GitHub Projects
- [ ] Community feature voting
- [ ] Quarterly major releases

---

## Conclusion

This project is **NOT currently ready** for public release due to:
1. **Security**: Hardcoded credentials and CloudIds throughout
2. **Specificity**: Heavy CiteMed-specific references
3. **Documentation**: Assumes CiteMed context

**Estimated Timeline**: 2-3 weeks of focused refactoring

**Recommended Next Step**: Start with **Option A (In-Place Refactoring)** beginning with Phase 1 security cleanup.

---

**Document Prepared By**: Claude Sonnet 4.5
**Review Required**: Security team review before public release
**Next Update**: After Phase 1 completion