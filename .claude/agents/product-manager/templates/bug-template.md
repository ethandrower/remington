# Bug Report Template

## Title
Bug: [Concise description of the issue]

## Summary
[One-sentence description of the problem and its impact]

## Steps to Reproduce
1. [First step - be specific about user actions]
2. [Second step - include any data or configuration needed]
3. [Third step - describe the action that triggers the bug]
4. [Additional steps as needed]

## Expected Behavior
[Clear description of what should happen when following the steps above]

## Actual Behavior
[Clear description of what actually happens - include error messages if any]

## Environment
- **Browser/Version:** [e.g., Chrome 120, Firefox 121, Safari 17]
- **User Role:** [e.g., Regulatory Affairs Specialist, Medical Affairs Manager]
- **Module:** [e.g., CiteSource, Literature, Dashboard]
- **Platform:** [e.g., Web, Word Add-in]
- **Date First Observed:** [When was this first noticed]

## Impact

### Severity
- [ ] **Critical** - System is unusable, data loss, security issue
- [ ] **High** - Major feature broken, significant user impact, no workaround
- [ ] **Medium** - Feature partially broken, workaround available
- [ ] **Low** - Minor issue, cosmetic problem, minimal impact

### Users Affected
- **Number/Percentage:** [e.g., "All users", "~15% of users", "3 enterprise customers"]
- **User Segment:** [e.g., "Users with special characters in names", "Safari users only"]

### Workaround
- **Available:** [Yes/No]
- **Description:** [If yes, describe the workaround steps]

## Technical Details

### Error Messages
```
[Paste any error messages from console, logs, or UI]
```

### Console Logs (if applicable)
```
[Paste relevant browser console errors or backend logs]
```

### Related Components
- **Affected Models:** [Django models involved]
- **Affected Views/API Endpoints:** [Backend endpoints with issues]
- **Affected Frontend Components:** [React/Vue components]
- **Database Tables:** [Tables with data issues]

### Potential Cause
[If known - hypothesis about what might be causing the issue]

### Related Tickets
- [Link to related bugs or features]
- [Link to original implementation ticket if regression]

## Acceptance Criteria

### Bug Fix Verification
- [ ] Bug is reproducible in test environment before fix
- [ ] Fix implemented following steps above
- [ ] Bug no longer occurs after fix
- [ ] No regressions introduced in related functionality
- [ ] Edge cases identified and handled
- [ ] Works across all supported browsers/platforms

### Testing Requirements
- [ ] Unit tests added for bug scenario
- [ ] Integration tests cover the fix
- [ ] Manual testing completed with screenshots/video
- [ ] Tested with different user roles
- [ ] Tested in production-like environment

### Documentation
- [ ] Root cause documented in ticket comments
- [ ] Technical approach documented
- [ ] Release notes updated (if customer-facing)

## Additional Context

### Screenshots/Videos
[Attach screenshots showing the bug or link to screen recording]

### Sample Data
[If relevant - provide sample data that triggers the bug, anonymized if needed]

### Customer Reports
[Link to customer support tickets or feedback related to this bug]

---

**Reported By:** [Name]
**Assigned To:** [Developer]
**Priority:** [Highest/High/Medium/Low]
**Target Fix Version:** [Sprint/Release]
**Date Reported:** [Date]
