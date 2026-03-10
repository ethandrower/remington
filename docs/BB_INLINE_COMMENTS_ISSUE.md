# Feature Request: Support for Inline Comment Detection and Reply

## Problem

Currently, when monitoring Bitbucket PR activity for @mentions, the `get_activity()` method returns comment objects but doesn't expose inline comment metadata (file path, line numbers). This prevents bots from:

1. **Detecting** that a comment is inline (vs. general PR comment)
2. **Replying inline** to the same code location

## Current Behavior

When a user posts an inline comment like:
```
@Remington Service Account can you explain this function?
```
On file `src/app.py` line 42, the bot:
- ✅ Detects the @mention
- ✅ Processes the request
- ❌ Replies as a **general PR comment** (not inline)

## Expected Behavior

The bot should:
1. Detect that the comment is inline
2. Extract file path and line number
3. Reply inline to the same location using `bb-pr comment --file src/app.py --line 42`

## API Data Available

Bitbucket's REST API returns inline comment metadata in the activity response:
```json
{
  "comment": {
    "id": 12345,
    "content": {...},
    "inline": {
      "path": "src/app.py",
      "from": 42,
      "to": 42
    }
  }
}
```

## Proposed Solution

### 1. Enhance `get_activity()` Return Data

Update `bitbucket_cli/api.py` to include inline metadata:

```python
def get_activity(self, workspace: str, repo: str, pr_id: int) -> List[Dict]:
    """Get PR activity with inline comment metadata"""
    # ... existing code ...

    activities = []
    for item in data.get("values", []):
        if item.get("comment"):
            comment = item["comment"]
            activity = {
                "comment": comment,
                "id": comment["id"],
                "content": comment.get("content", {}),
                # NEW: Include inline metadata if present
                "inline": comment.get("inline"),  # None for general comments
            }
            activities.append(activity)

    return activities
```

### 2. Enhance `add_comment()` to Support Inline Replies

The `bb-pr comment` CLI already supports inline comments via:
- `--file TEXT` - File path
- `--line INTEGER` - Line number
- `--from-line INTEGER` / `--to-line INTEGER` - Multi-line

Ensure the Python API wrapper supports these parameters:

```python
def add_comment(
    self,
    workspace: str,
    repo: str,
    pr_id: int,
    message: str,
    file_path: Optional[str] = None,  # NEW
    line: Optional[int] = None,        # NEW
    from_line: Optional[int] = None,   # NEW
    to_line: Optional[int] = None,     # NEW
) -> Dict:
    """Add comment (general or inline) to a PR"""
    cmd = ["bb-pr", "comment", str(pr_id), "-m", message]

    if file_path:
        cmd.extend(["--file", file_path])
    if line:
        cmd.extend(["--line", str(line)])
    if from_line and to_line:
        cmd.extend(["--from-line", str(from_line), "--to-line", str(to_line)])

    # ... execute command ...
```

## Use Case

**Scenario:** User asks inline code question

```python
# src/app.py line 42
def process_payment(amount):  # @Remington Service Account what validation should we add here?
    return charge_card(amount)
```

**Bot should reply inline at line 42:**
```
You should add validation for:
1. Amount > 0
2. Amount <= max_transaction_limit
3. Payment method exists and is active
```

Instead of posting this as a general PR comment.

## Acceptance Criteria

- [ ] `get_activity()` returns inline metadata when present
- [ ] `add_comment()` accepts optional file/line parameters
- [ ] Example/test demonstrating inline comment detection and reply
- [ ] Documentation updated with inline comment usage

## Priority

Medium - This improves UX significantly for code review bots but doesn't block basic functionality.

## Related

The `bb-pr comment` CLI already supports these flags - we just need to expose them in the Python API wrapper.

---

**Issue Link:** https://github.com/ethandrower/bitbucket-cli-claude-code/issues/new

**Copy the content above and paste into the GitHub issue form.**
