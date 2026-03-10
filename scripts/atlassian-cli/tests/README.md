# Atlassian CLI Test Suite

Comprehensive pytest test suite for validating Jira CLI functionality against the live Atlassian API.

## Overview

This test suite validates:
- ✅ **CRUD Operations** - Create, Read, Update, Delete issues
- ✅ **Subtasks** - Create and manage subtasks
- ✅ **Comments** - Add, read, update, delete comments
- ✅ **Transitions** - Move issues through workflow states
- ✅ **Search** - JQL queries and user search
- ✅ **Cleanup** - Automatic deletion of test data

## Prerequisites

### 1. Dependencies

```bash
cd /Users/ethand320/code/citemed/project-manager
pip install pytest pytest-timeout requests python-dotenv
```

### 2. Environment Configuration

Ensure your `.env` file has valid credentials:

```bash
ATLASSIAN_SERVICE_ACCOUNT_EMAIL=your-email@atlassian.com
ATLASSIAN_SERVICE_ACCOUNT_TOKEN=your_api_token
ATLASSIAN_CLOUD_ID=67bbfd03-b309-414f-9640-908213f80628
```

### 3. Optional: Test Project

Set a specific project for testing (defaults to `ECD`):

```bash
export TEST_PROJECT_KEY=ECD
```

## Running Tests

### Run All Tests

```bash
cd scripts/atlassian-cli
pytest tests/
```

### Run Specific Test Categories

```bash
# Only CRUD tests
pytest tests/test_issue_crud.py

# Only comment tests
pytest tests/test_comments.py

# Only transition tests
pytest tests/test_transitions.py

# Only search tests
pytest tests/test_search.py
```

### Run Specific Tests

```bash
# Run a single test
pytest tests/test_issue_crud.py::TestIssueCreate::test_create_basic_issue

# Run a test class
pytest tests/test_comments.py::TestCommentOperations
```

### Verbose Output

```bash
# Extra verbose
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show full tracebacks
pytest tests/ --tb=long
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4
```

## Test Structure

```
tests/
├── conftest.py              # Fixtures and test configuration
├── pytest.ini               # Pytest settings
├── test_issue_crud.py       # Create, read, update, delete tests
├── test_comments.py         # Comment operations
├── test_transitions.py      # Workflow transitions
├── test_search.py           # JQL and user search
└── README.md                # This file
```

## Test Coverage

### test_issue_crud.py (11 tests)

**Create Operations:**
- ✅ Create basic issue
- ✅ Create issue with description
- ✅ Create subtask under parent

**Read Operations:**
- ✅ Get existing issue
- ✅ Get non-existent issue (error handling)

**Update Operations:**
- ✅ Update summary
- ✅ Update description
- ✅ Update multiple fields

**Delete Operations:**
- ✅ Delete issue
- ✅ Delete non-existent issue

### test_comments.py (6 tests)

- ✅ Add simple comment
- ✅ Add comment with user mention
- ✅ Add multiple comments
- ✅ Read all comments from issue
- ✅ Update existing comment
- ✅ Delete comment

### test_transitions.py (8 tests)

**Transition Operations:**
- ✅ Get available transitions
- ✅ Transition to new status
- ✅ Transition to Done
- ✅ Invalid transition error handling
- ✅ Multi-step workflow navigation

**Workflow Validation:**
- ✅ Transitions preserve other fields
- ✅ Get status categories

### test_search.py (17 tests)

**JQL Search:**
- ✅ Search by project
- ✅ Search by issue key
- ✅ Search by summary text
- ✅ Search by status
- ✅ Search with ordering
- ✅ Search with field selection
- ✅ Search with max results
- ✅ Complex JQL queries
- ✅ No results handling
- ✅ Search created today

**User Search:**
- ✅ Search current user
- ✅ Search by partial email
- ✅ Search non-existent user

**Advanced Queries:**
- ✅ Search by assignee
- ✅ Search unassigned issues
- ✅ Search by issue type

## Fixtures

### Session-Scoped

- `jira_credentials` - Loads credentials from .env
- `test_project_key` - Project key for testing

### Function-Scoped

- `jira_client` - JiraClient instance with auto-cleanup
- `created_issues` - Tracks issues for cleanup
- `test_issue` - Pre-created test issue
- `test_parent_issue` - Pre-created parent for subtask tests

## Automatic Cleanup

All tests use fixtures that **automatically delete created issues** after each test:

```python
def test_example(jira_client, created_issues):
    result = jira_client.create_issue(...)
    created_issues.append(result['key'])  # Will be auto-deleted
```

The `jira_client` fixture handles cleanup in its teardown phase.

## Best Practices

### 1. Mark Test Issues

Always prefix test issue summaries with `[TEST]`:

```python
summary="[TEST] My test issue"
```

### 2. Use Fixtures for Setup

Don't create issues manually - use fixtures:

```python
def test_something(test_issue):  # Issue auto-created and cleaned up
    issue_key = test_issue['key']
    # ... test logic
```

### 3. Handle Workflow Variations

Different Jira instances have different workflows:

```python
if len(transitions) == 0:
    pytest.skip("No transitions available")
```

### 4. Add Created Issues to Tracker

Always track created issues for cleanup:

```python
created_issues.append(issue_key)
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Atlassian CLI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pytest-timeout requests python-dotenv
      - name: Run tests
        env:
          ATLASSIAN_SERVICE_ACCOUNT_EMAIL: ${{ secrets.JIRA_EMAIL }}
          ATLASSIAN_SERVICE_ACCOUNT_TOKEN: ${{ secrets.JIRA_TOKEN }}
          ATLASSIAN_CLOUD_ID: ${{ secrets.JIRA_CLOUD_ID }}
        run: |
          cd scripts/atlassian-cli
          pytest tests/
```

## Troubleshooting

### Tests Failing with 401 Unauthorized

Check your credentials:
```bash
source ../../.env
echo $ATLASSIAN_SERVICE_ACCOUNT_EMAIL
echo $ATLASSIAN_SERVICE_ACCOUNT_TOKEN
```

### Tests Failing with 404 Not Found

Verify project key exists:
```bash
./jira-cli search "project = ECD" --max-results 1
```

### Tests Timing Out

Increase timeout in pytest.ini or skip slow tests:
```bash
pytest tests/ --timeout=120
```

### Cleanup Issues

If tests are interrupted, manually clean up test issues:
```bash
./jira-cli search 'project = ECD AND summary ~ "[TEST]"' | grep ECD-
# Then delete each: ./jira-cli issue delete ECD-XXX
```

Or use the cleanup script:
```bash
# Create cleanup script
for issue in $(./jira-cli search 'summary ~ "[TEST]"' --json | jq -r '.issues[].key'); do
  echo "Deleting $issue"
  curl -X DELETE -u "$ATLASSIAN_SERVICE_ACCOUNT_EMAIL:$ATLASSIAN_SERVICE_ACCOUNT_TOKEN" \
    "https://citemed.atlassian.net/rest/api/3/issue/$issue"
done
```

## Coverage Report

To generate coverage report:

```bash
pip install pytest-cov

pytest tests/ --cov=. --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html
```

## Performance Testing

Run tests with timing information:

```bash
pytest tests/ --durations=10
```

## Future Enhancements

Potential additions to the test suite:

- [ ] Test issue linking
- [ ] Test attachments
- [ ] Test custom fields
- [ ] Test bulk operations
- [ ] Test pagination for large result sets
- [ ] Test rate limiting behavior
- [ ] Test concurrent operations
- [ ] Mock mode for offline testing
- [ ] Performance benchmarks
- [ ] Confluence CLI tests

## Contributing

When adding new tests:

1. Follow existing patterns (fixtures, cleanup, naming)
2. Add docstrings explaining what's being tested
3. Use meaningful assertion messages
4. Handle workflow variations gracefully
5. Clean up all created resources
6. Update this README with new test descriptions

---

**Total Tests:** 42+ comprehensive tests
**Estimated Runtime:** 2-5 minutes (depends on API latency)
**Last Updated:** 2025-10-21
