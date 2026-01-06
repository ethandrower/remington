# Contributing to Autonomous Project Manager

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

---

## 🎯 Quick Start

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/project-manager.git
   cd project-manager
   ```
3. **Set up development environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```
4. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
5. **Make your changes**
6. **Run tests**
   ```bash
   pytest tests/ -v
   ```
7. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request**

---

## 📋 Code of Conduct

### Our Standards

- **Be respectful** - Treat all contributors with respect and kindness
- **Be collaborative** - Work together to improve the project
- **Be constructive** - Provide helpful feedback and suggestions
- **Be patient** - Remember that everyone was a beginner once
- **Be inclusive** - Welcome people of all backgrounds and experience levels

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Publishing others' private information
- Any conduct that could reasonably be considered inappropriate

---

## 🐛 Reporting Bugs

### Before Submitting

1. **Check existing issues** - Search for similar issues first
2. **Try latest version** - Ensure you're using the most recent release
3. **Reproduce the bug** - Verify you can consistently reproduce it
4. **Collect information** - Gather logs, configuration, and error messages

### Bug Report Template

When creating a bug report, include:

```markdown
## Bug Description
Clear and concise description of the bug.

## Steps to Reproduce
1. Go to '...'
2. Run command '...'
3. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.5]
- Claude Code Version: [e.g., 2.0.25]
- Project Version: [e.g., 1.0.0]

## Logs
```
Paste relevant logs here
```

## Additional Context
Any other relevant information.
```

---

## 💡 Suggesting Features

### Feature Request Template

```markdown
## Feature Description
Clear and concise description of the feature.

## Problem it Solves
Explain the problem or use case this addresses.

## Proposed Solution
Describe how the feature would work.

## Alternatives Considered
Other approaches you've thought about.

## Additional Context
Mockups, examples, or references.
```

### Feature Proposal Process

1. **Open an issue** with the feature request template
2. **Discuss with maintainers** - Get feedback before implementation
3. **Create implementation plan** - Outline technical approach
4. **Get approval** - Wait for maintainer approval before starting
5. **Submit PR** - Follow contribution guidelines below

---

## 🔧 Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for MCP servers)
- Claude Code CLI
- Git
- Virtual environment tool

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/project-manager.git
cd project-manager

# Add upstream remote
git remote add upstream https://github.com/original/project-manager.git

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with test credentials

# Verify setup
python src/config.py
pytest tests/ -v
```

### Development Tools

**Recommended IDE Extensions:**
- Python (Microsoft)
- Pylance
- Python Debugger
- Black Formatter
- autoDocstring

**Optional Tools:**
- `pre-commit` - Git hook scripts
- `black` - Code formatting
- `flake8` - Linting
- `mypy` - Type checking
- `pytest-cov` - Code coverage

---

## 📝 Coding Standards

### Python Style Guide

We follow **PEP 8** with these specifics:

#### Code Formatting

```python
# Good: Clear, readable, well-documented
def fetch_jira_issue(issue_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch complete issue details from Jira

    Args:
        issue_key: Jira issue key (e.g., 'PROJ-123')

    Returns:
        Issue data dictionary or None if not found

    Raises:
        ConfigurationError: If Jira URL not configured
    """
    jira_url = get_jira_base_url()

    try:
        response = requests.get(f"{jira_url}/issue/{issue_key}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {issue_key}: {e}")
        return None
```

#### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`
- **Module names**: `lowercase` (no underscores if possible)

#### Type Hints

Always use type hints for function signatures:

```python
from typing import List, Dict, Optional, Any

def process_events(
    events: List[Dict[str, Any]],
    max_retries: int = 3
) -> Optional[Dict[str, Any]]:
    pass
```

#### Docstrings

Use Google-style docstrings:

```python
def calculate_sla_breach(
    created_at: datetime,
    target_hours: int
) -> bool:
    """
    Determine if an SLA has been breached

    Args:
        created_at: Timestamp when item was created
        target_hours: SLA target in business hours

    Returns:
        True if SLA breached, False otherwise

    Example:
        >>> created = datetime(2025, 1, 1, 9, 0)
        >>> calculate_sla_breach(created, 24)
        False
    """
    pass
```

#### Error Handling

```python
# Good: Specific exceptions, informative messages
try:
    config = get_atlassian_config()
except ConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    raise

# Avoid: Bare except
try:
    do_something()
except:  # Bad - too broad
    pass
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Detailed diagnostic info")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.critical("Critical failures")

# Include context
logger.info(f"Processing ticket {issue_key} from user {user_id}")
```

---

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
├── integration/       # Integration tests (slower, multiple components)
├── e2e/              # End-to-end tests (full system)
└── conftest.py       # Shared fixtures
```

### Writing Tests

```python
import pytest
from src.config import get_atlassian_config, ConfigurationError

class TestAtlassianConfig:
    """Tests for Atlassian configuration"""

    def test_get_config_success(self, monkeypatch):
        """Test successful config retrieval"""
        monkeypatch.setenv('ATLASSIAN_CLOUD_ID', 'test-cloud-id')
        monkeypatch.setenv('JIRA_INSTANCE_URL', 'https://test.atlassian.net')
        monkeypatch.setenv('ATLASSIAN_PROJECT_KEY', 'TEST')

        config = get_atlassian_config()

        assert config['cloud_id'] == 'test-cloud-id'
        assert config['jira_url'] == 'https://test.atlassian.net'
        assert config['project_key'] == 'TEST'

    def test_get_config_missing_cloud_id(self, monkeypatch):
        """Test error when cloud ID missing"""
        monkeypatch.delenv('ATLASSIAN_CLOUD_ID', raising=False)

        with pytest.raises(ConfigurationError, match="ATLASSIAN_CLOUD_ID"):
            get_atlassian_config()
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_config.py -v

# Run specific test
pytest tests/unit/test_config.py::TestAtlassianConfig::test_get_config_success -v

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run in parallel (faster)
pytest -n auto tests/
```

### Test Coverage

- **Aim for 80%+ coverage** for new code
- **100% coverage** for critical paths (configuration, authentication, data integrity)
- **Focus on behavior**, not just line coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing tests/

# View HTML report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

---

## 📦 Pull Request Process

### Before Submitting

1. **Update from upstream**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run full test suite**
   ```bash
   pytest tests/ -v
   ```

3. **Run linters** (if configured)
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

4. **Update documentation**
   - Update README.md if adding features
   - Add/update docstrings
   - Update .claude/ documentation if needed

5. **Commit messages**
   Follow Conventional Commits:
   ```
   feat: Add new SLA monitoring feature
   fix: Resolve database locking issue
   docs: Update configuration guide
   test: Add tests for Jira integration
   refactor: Simplify orchestrator logic
   chore: Update dependencies
   ```

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran.

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] Any dependent changes have been merged

## Screenshots (if applicable)
Add screenshots for UI changes.

## Additional Notes
Any other relevant information.
```

### Review Process

1. **Automated checks** - CI/CD must pass
2. **Code review** - At least one maintainer approval required
3. **Testing** - Reviewer may test changes locally
4. **Documentation** - Ensure docs are updated
5. **Merge** - Maintainer will merge once approved

---

## 🏗️ Project Architecture

### Directory Structure

```
src/
├── config.py              # Configuration management
├── pm_agent_service.py    # Main service entry point
├── monitors/              # Event polling
│   ├── jira_monitor.py
│   ├── slack_monitor.py
│   └── bitbucket_monitor.py
├── orchestration/         # Claude Code integration
├── database/              # Data models
└── web/                   # Webhook server
```

### Key Components

**Configuration (`src/config.py`)**
- Centralized environment variable management
- Validation and error handling
- Convenience methods for common config

**Monitors (`src/monitors/`)**
- Poll external services (Jira, Slack, Bitbucket)
- Deduplication via SQLite
- 3-day lookback window

**Orchestration (`src/orchestration/`)**
- Claude Code CLI integration
- MCP tool usage
- Context-aware decision making

**Web (`src/web/`)**
- FastAPI webhook server
- Event queuing
- Health checks

---

## 📚 Documentation

### Updating Documentation

When making changes, update:

1. **README.md** - For user-facing features
2. **CONTRIBUTING.md** - For contributor guidelines
3. **docs/** - For detailed guides
4. **.claude/** - For agent instructions
5. **Docstrings** - For code documentation

### Documentation Standards

- **Clear and concise** - Easy to understand
- **Examples** - Show, don't just tell
- **Up-to-date** - Keep in sync with code
- **Well-organized** - Logical structure

---

## 🔄 Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** - Breaking changes (2.0.0)
- **MINOR** - New features (1.1.0)
- **PATCH** - Bug fixes (1.0.1)

### Creating a Release

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. Create GitHub release with notes

---

## 💬 Communication

### Getting Help

- **GitHub Discussions** - General questions and discussions
- **GitHub Issues** - Bug reports and feature requests
- **Discord/Slack** - Real-time chat (if available)

### Response Times

- **Bug reports** - 2-3 business days
- **Feature requests** - 1 week
- **Pull requests** - 3-5 business days

---

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Thanked in project README

---

## 📖 Additional Resources

- [Python PEP 8 Style Guide](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Claude Code Documentation](https://claude.com/claude-code/docs)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## ❓ Questions?

If you have questions not covered here:

1. Check the [README](README.md)
2. Search [existing issues](https://github.com/yourusername/project-manager/issues)
3. Ask in [GitHub Discussions](https://github.com/yourusername/project-manager/discussions)
4. Open a new issue

---

**Thank you for contributing! 🎉**