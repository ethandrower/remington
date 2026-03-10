# Feature Request: Configurable SDLC Workflow Definition

## Problem Statement

Currently, Remington's SLA monitoring and workflow enforcement is **hardcoded for a specific SDLC**:
- Status names: "Draft", "In Progress", "In QA", "Pending Approval", "Done"
- SLA thresholds: 48h for QA, 24h for PR review, etc.
- Escalation rules: 4-level matrix with fixed timings
- Definition of Done: Implicit, not explicitly defined

**This limits adoption** because:
1. Every team has different status names (e.g., "Code Review" vs "Pending Approval")
2. Different teams need different SLA targets (startup vs enterprise)
3. Teams have unique workflow stages (some have UAT, some don't)
4. Compliance requirements vary (HIPAA, SOC2, etc.)

**Example scenarios where current implementation fails:**
- Team uses "Ready for QA" instead of "In QA" → SLA monitoring doesn't work
- Team needs 72h QA turnaround instead of 48h → Must modify source code
- Team has "Needs Rework" status → No SLA defined for this
- Team requires mandatory security review stage → Can't add to workflow

---

## Proposed Solution

### Create SDLC Configuration File

Allow teams to define their complete SDLC in a configuration file: `.claude/sdlc-config.yaml`

This would replace hardcoded workflow logic with **user-defined, declarative configuration**.

---

## Configuration Schema

### Example: `sdlc-config.yaml`

```yaml
# Team-specific SDLC Configuration
# Defines workflow stages, SLAs, and enforcement rules

sdlc:
  name: "CiteMed Agile Sprint Workflow"
  version: "1.0"

  # Jira project this applies to
  project_key: "ECD"

  # Business hours for SLA calculation
  business_hours:
    timezone: "America/New_York"
    start: 9  # 9 AM
    end: 17   # 5 PM
    holidays:
      - "2025-01-01"  # New Year
      - "2025-07-04"  # Independence Day
      - "2025-12-25"  # Christmas

  # Define workflow stages
  stages:
    - id: "draft"
      jira_status: "Draft"
      description: "Ticket is being written and refined"
      entry_requirements:
        - "Title is descriptive"
        - "Description exists"
      exit_criteria:
        - "Acceptance criteria defined"
        - "Estimate provided"
      sla:
        max_time_in_stage: null  # No time limit
        comment_response_time: 72h
      escalation:
        enabled: false

    - id: "ready_for_dev"
      jira_status: "Ready for Development"
      description: "Refinement complete, ready to be picked up"
      entry_requirements:
        - "All exit criteria from 'draft' met"
        - "Priority assigned"
      exit_criteria:
        - "Developer assigned"
        - "Moved to In Progress"
      sla:
        max_time_in_stage: null
        comment_response_time: 48h
      escalation:
        enabled: false

    - id: "in_progress"
      jira_status: "In Progress"
      description: "Active development work"
      entry_requirements:
        - "Developer assigned"
        - "Branch created (naming: ECD-XXX-description)"
      exit_criteria:
        - "Code complete"
        - "Unit tests pass"
        - "PR created and linked"
      sla:
        max_time_in_stage: 5d  # Alert if stuck > 5 business days
        max_time_without_commit: 2d  # Alert if no git activity
        comment_response_time: 24h
      escalation:
        enabled: true
        levels:
          - threshold: 3d
            severity: "warning"
            action: "jira_comment"
            message: "This ticket has been In Progress for {days} days. Can you provide a status update?"
          - threshold: 5d
            severity: "critical"
            action: "jira_comment_and_slack"
            notify: ["assignee", "tech_lead"]

    - id: "code_review"
      jira_status: "Code Review"
      description: "PR is open and awaiting review"
      entry_requirements:
        - "PR created and linked in ticket"
        - "CI/CD pipeline passing"
        - "Self-review complete"
      exit_criteria:
        - "PR approved by at least 1 reviewer"
        - "All review comments addressed"
        - "Conflicts resolved"
      sla:
        max_time_in_stage: 48h  # PR must be reviewed within 2 days
        comment_response_time: 24h  # Respond to review feedback within 1 day
      escalation:
        enabled: true
        levels:
          - threshold: 36h
            severity: "warning"
            action: "slack_reminder"
            notify: ["assignee"]
          - threshold: 48h
            severity: "critical"
            action: "jira_comment_and_slack"
            notify: ["assignee", "tech_lead"]

    - id: "qa"
      jira_status: "In QA"
      description: "Ticket is being tested by QA team"
      entry_requirements:
        - "PR merged to main"
        - "Deployed to QA environment"
        - "Test plan exists"
      exit_criteria:
        - "All test cases pass"
        - "No critical bugs found"
        - "Sign-off from QA lead"
      sla:
        max_time_in_stage: 48h  # QA must complete within 2 days
        max_time_without_update: 24h  # Daily updates required
        comment_response_time: 24h
      escalation:
        enabled: true
        owner: "qa_lead"  # Joshua for CiteMed
        levels:
          - threshold: 36h
            severity: "warning"
            action: "slack_reminder"
            notify: ["qa_lead"]
            message: "QA has been in progress for {hours}h. Target is 48h."
          - threshold: 48h
            severity: "critical"
            action: "jira_comment_and_slack"
            notify: ["qa_lead", "assignee", "product_manager"]
          - threshold: 72h
            severity: "blocker"
            action: "escalate_to_leadership"
            notify: ["qa_lead", "assignee", "product_manager", "cto"]

    - id: "needs_fix"
      jira_status: "Needs Fix"
      description: "QA found issues that need to be addressed"
      entry_requirements:
        - "QA test failures documented"
        - "Bugs linked or described in comments"
      exit_criteria:
        - "Fixes implemented"
        - "Re-deployed to QA environment"
        - "Transitioned back to QA"
      sla:
        max_time_in_stage: 24h  # Quick turnaround expected
        comment_response_time: 8h  # Urgent - respond quickly
      escalation:
        enabled: true
        levels:
          - threshold: 24h
            severity: "critical"
            action: "jira_comment_and_slack"
            notify: ["assignee"]

    - id: "pending_approval"
      jira_status: "Pending Approval"
      description: "Awaiting stakeholder/PM approval for deployment"
      entry_requirements:
        - "QA complete and approved"
        - "Stakeholder review requested"
      exit_criteria:
        - "Approval received from stakeholder"
        - "Deployment scheduled"
      sla:
        max_time_in_stage: 48h  # Don't let approvals sit
        comment_response_time: 24h
      escalation:
        enabled: true
        owner: "product_manager"
        levels:
          - threshold: 48h
            severity: "warning"
            action: "slack_reminder"
            notify: ["product_manager"]
          - threshold: 72h
            severity: "critical"
            action: "escalate_to_leadership"

    - id: "done"
      jira_status: "Done"
      description: "Work complete and deployed to production"
      entry_requirements:
        - "Deployed to production"
        - "Deployment verified"
        - "Documentation updated"
      exit_criteria: null  # Terminal state
      sla: null  # No SLAs for completed work
      escalation:
        enabled: false

  # Cross-cutting SLA rules (apply to ALL stages unless overridden)
  global_slas:
    - type: "blocked_ticket_update"
      applies_when: "Ticket has 'blocked' flag OR status contains 'Blocked'"
      requirement: "Daily comment update explaining blocker status"
      max_time_without_update: 24h
      escalation:
        - threshold: 24h
          action: "jira_comment"
        - threshold: 48h
          action: "jira_comment_and_slack"
          notify: ["assignee", "tech_lead"]

    - type: "comment_response"
      applies_when: "New comment from stakeholder/PM/customer"
      requirement: "Developer must respond within SLA"
      # Default overridden by stage-specific comment_response_time
      default_response_time: 48h

    - type: "pr_feedback_response"
      applies_when: "PR has new review comments"
      requirement: "Developer addresses feedback within SLA"
      critical_changes: 4h
      feature_prs: 24h
      non_urgent: 48h

  # Bot behavior configuration
  bot_settings:
    dry_run: false
    alert_channel: "#pm-agent-standup"
    alert_cooldown: 24h  # Don't spam - max 1 alert per violation per 24h
    mention_format: "[~accountid:{account_id}]"  # Jira mention format

  # Validation rules (checked when tickets transition)
  validation:
    require_pr_link_before_qa: true
    require_acceptance_criteria: true
    require_assignee_for_in_progress: true
    block_transitions_if_validation_fails: false  # Warning only
```

---

## Implementation Design

### 1. Configuration Loading

**File:** `src/config.py`

```python
import yaml
from pathlib import Path
from typing import Dict, List, Optional

class SDLCConfig:
    """Load and validate SDLC configuration"""

    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path(".claude/sdlc-config.yaml")

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.validate()

    def get_stage(self, jira_status: str) -> Optional[Dict]:
        """Get stage config by Jira status name"""
        for stage in self.config['sdlc']['stages']:
            if stage['jira_status'] == jira_status:
                return stage
        return None

    def get_sla_for_stage(self, stage_id: str) -> Dict:
        """Get SLA configuration for a stage"""
        stage = self.get_stage_by_id(stage_id)
        return stage.get('sla', {})

    def get_escalation_levels(self, stage_id: str) -> List[Dict]:
        """Get escalation levels for a stage"""
        stage = self.get_stage_by_id(stage_id)
        escalation = stage.get('escalation', {})
        return escalation.get('levels', []) if escalation.get('enabled') else []
```

### 2. SLA Monitoring Updates

**File:** `scripts/core/sla_check_working.py`

**Current (Hardcoded):**
```python
# Check if in "Pending Approval" status for > 48 hours
if status == "Pending Approval":
    time_in_status = calculate_time_in_status(ticket)
    if time_in_status > 48 * 3600:
        violations.append({...})
```

**New (Config-Driven):**
```python
from src.config import SDLCConfig

sdlc = SDLCConfig()

# For each ticket
for ticket in tickets:
    status = ticket['status']
    stage = sdlc.get_stage(status)

    if stage and stage['sla']:
        sla = stage['sla']

        # Check max_time_in_stage
        if sla.get('max_time_in_stage'):
            time_in_status = calculate_time_in_status(ticket)
            threshold = parse_duration(sla['max_time_in_stage'])  # "48h" → 172800 seconds

            if time_in_status > threshold:
                # Get escalation level
                levels = sdlc.get_escalation_levels(stage['id'])
                severity = get_severity_for_overage(time_in_status, threshold, levels)

                violations.append({
                    'type': f"{stage['id']}_time_limit",
                    'severity': severity,
                    'item_id': ticket['key'],
                    'stage': stage['id'],
                    'hours_overdue': (time_in_status - threshold) / 3600,
                    'sla_target': sla['max_time_in_stage'],
                    'message': stage.get('escalation', {}).get('levels', [{}])[0].get('message', '').format(
                        days=(time_in_status / 86400),
                        hours=(time_in_status / 3600)
                    )
                })
```

### 3. Validation Engine

**File:** `src/validation/sdlc_validator.py` (new)

```python
class SDLCValidator:
    """Validate ticket transitions against SDLC rules"""

    def __init__(self, sdlc_config: SDLCConfig):
        self.sdlc = sdlc_config

    def validate_transition(self, ticket: Dict, from_status: str, to_status: str) -> ValidationResult:
        """Check if transition is valid"""
        target_stage = self.sdlc.get_stage(to_status)

        if not target_stage:
            return ValidationResult(valid=False, error=f"Unknown status: {to_status}")

        # Check entry requirements
        entry_reqs = target_stage.get('entry_requirements', [])
        for req in entry_reqs:
            if not self.check_requirement(ticket, req):
                return ValidationResult(
                    valid=False,
                    warning=f"Entry requirement not met: {req}",
                    blocking=self.sdlc.config['sdlc']['validation'].get('block_transitions_if_validation_fails', False)
                )

        return ValidationResult(valid=True)

    def check_requirement(self, ticket: Dict, requirement: str) -> bool:
        """Check if specific requirement is met"""
        # Examples:
        # "PR created and linked" → Check if custom field has PR URL
        # "All test cases pass" → Check test execution results
        # "Approval received" → Check approval custom field

        # This would use pattern matching or custom validators
        pass
```

### 4. Claude Code Integration

Update the unified `process_mention()` prompt to include SDLC awareness:

```python
# In orchestrator.py - process_mention()

sdlc = SDLCConfig()
current_stage = sdlc.get_stage(ticket_status)

prompt += f"""
SDLC CONTEXT:
Current Stage: {current_stage['id']} ({current_stage['jira_status']})
Description: {current_stage['description']}

Entry Requirements (should already be met):
{format_list(current_stage['entry_requirements'])}

Exit Criteria (what needs to happen before moving to next stage):
{format_list(current_stage['exit_criteria'])}

SLA for this stage:
- Max time in stage: {current_stage['sla']['max_time_in_stage']}
- Comment response time: {current_stage['sla']['comment_response_time']}

If the user asks about status, next steps, or what's needed - refer to the exit criteria above.
"""
```

---

## Benefits

### For Teams
1. **Zero Code Changes** - Configure via YAML, no Python editing
2. **Instant Adoption** - Works with any Jira workflow
3. **Compliance Ready** - Define audit requirements per stage
4. **Flexible SLAs** - Different targets for different stages
5. **Custom Escalations** - Define who gets notified and when

### For Remington
1. **Universal Appeal** - Not just CiteMed-specific
2. **Open Source Ready** - Any team can use it
3. **Easier Maintenance** - Config changes don't require code deploys
4. **Self-Documenting** - YAML file becomes workflow documentation
5. **Testable** - Easy to unit test different SDLC scenarios

### For Bot Intelligence
1. **Context-Aware** - Claude knows stage definitions
2. **Guided Transitions** - Can advise on exit criteria
3. **Proactive Validation** - Warns before invalid transitions
4. **Better Escalations** - Stage-specific messaging

---

## Acceptance Criteria

- [ ] Create `SDLCConfig` class that loads YAML configuration
- [ ] Define YAML schema with examples for 3+ different team workflows:
  - Startup (simple: Draft → Dev → Review → Done)
  - Enterprise (complex: includes UAT, security review, compliance)
  - Open Source (public review, community approval)
- [ ] Update SLA monitoring to use config instead of hardcoded values
- [ ] Support all existing SLA types from current implementation
- [ ] Add validation engine that checks entry/exit criteria
- [ ] Create migration guide from hardcoded → config-driven
- [ ] Add schema validation (validate YAML on load, fail fast with helpful errors)
- [ ] Update documentation with configuration examples
- [ ] Backward compatibility: if no config file, use hardcoded defaults
- [ ] Integration test suite covering:
  - Loading valid configs
  - Rejecting invalid configs
  - SLA monitoring across different stage configs
  - Escalation with custom thresholds
  - Validation of transitions

---

## Future Enhancements

### Phase 2 - Visual SDLC Designer
- Web UI to visually design workflow
- Drag-and-drop stage configuration
- Export to YAML

### Phase 3 - SDLC Templates
- Pre-built configs for common frameworks:
  - Scrum
  - Kanban
  - Waterfall
  - SAFe (Scaled Agile)
- Industry-specific templates (healthcare, finance, e-commerce)

### Phase 4 - Multi-Project Support
- Different SDLC per Jira project
- Shared vs. project-specific SLAs
- Cross-project dependencies

### Phase 5 - Analytics & Optimization
- Detect bottleneck stages from historical data
- Suggest SLA adjustments based on team velocity
- Automatic SLA tuning (machine learning)

---

## Example Use Cases

### Use Case 1: Security-Conscious Team
```yaml
stages:
  - id: "security_review"
    jira_status: "Security Review"
    entry_requirements:
      - "SAST scan complete"
      - "Dependencies scanned for vulnerabilities"
      - "Security champion assigned"
    sla:
      max_time_in_stage: 24h  # Fast turnaround required
    escalation:
      notify: ["security_team", "ciso"]
```

### Use Case 2: Compliance-Heavy Team
```yaml
stages:
  - id: "sox_compliance_check"
    jira_status: "SOX Review"
    entry_requirements:
      - "Change control form submitted"
      - "Risk assessment complete"
      - "Audit trail documented"
    exit_criteria:
      - "SOX compliance officer approval"
      - "Change advisory board (CAB) approval"
    sla:
      max_time_in_stage: 5d  # Compliance takes time
```

### Use Case 3: High-Velocity Startup
```yaml
# Minimal stages, fast turnaround
stages:
  - id: "dev"
    sla:
      max_time_in_stage: 1d  # Ship fast!
  - id: "review"
    sla:
      max_time_in_stage: 2h  # Quick reviews
```

---

## Migration Path

### For Existing Remington Users

1. **Generate default config** from current hardcoded values:
   ```bash
   python scripts/utilities/generate_sdlc_config.py > .claude/sdlc-config.yaml
   ```

2. **Customize** the generated YAML to match your workflow

3. **Test** in dry-run mode:
   ```bash
   DRY_RUN=true python scripts/core/sla_check_working.py
   ```

4. **Deploy** - Remove hardcoded values, use config

### For New Users

1. **Choose template** or start from example
2. **Customize** stage names, SLAs, escalations
3. **Run validation**:
   ```bash
   python scripts/utilities/validate_sdlc_config.py
   ```
4. **Deploy** and monitor

---

## Technical Considerations

### Schema Validation
- Use `jsonschema` library to validate YAML against formal schema
- Provide helpful error messages (e.g., "Stage 'qa' references unknown owner 'qa_lead'")

### Performance
- Load config once at startup, cache in memory
- Reload on config file change (watch for modifications)
- Avoid re-parsing YAML on every SLA check

### Backward Compatibility
- If `.claude/sdlc-config.yaml` doesn't exist, fall back to hardcoded defaults
- Log warning: "Using default SDLC config. Create .claude/sdlc-config.yaml to customize."

### Testing Strategy
- Unit tests for config parsing
- Integration tests for SLA monitoring with different configs
- Snapshot tests (given config X, expect violations Y)

---

## Related Issues

- #TBD - QA time SLA monitoring (would be solved by this)
- #TBD - Custom status names not recognized (would be solved by this)
- #TBD - Different SLA targets per team (would be solved by this)

---

## Priority

**High** - This would transform Remington from a CiteMed-specific tool to a **universal SDLC enforcement platform**.

---

**Labels:** `enhancement`, `configuration`, `sdlc`, `universal-adoption`, `good first issue` (for documentation parts)

---

## Questions for Discussion

1. Should we support multiple SDLC configs (per project)? Or one config per Remington instance?
2. Should validation be blocking (prevent transitions) or warning-only?
3. Should we generate config from existing Jira workflow automatically?
4. Should escalation messages support templates with variables (`{ticket_key}`, `{days_overdue}`, etc.)?
