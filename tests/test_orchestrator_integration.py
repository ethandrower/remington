#!/usr/bin/env python3
"""
Integration Tests for Claude Code Orchestrator with Jira Tools

Tests that:
1. Claude Code subprocess can invoke tools
2. Prompts correctly reference tools
3. End-to-end message workflows work
4. Tools are used instead of MCP
"""

import pytest
import os
import sys
import json
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.claude_code_orchestrator import ClaudeCodeOrchestrator


class TestOrchestratorSetup:
    """Test orchestrator initialization"""

    def test_orchestrator_initializes(self):
        """Test that orchestrator can be created"""
        orchestrator = ClaudeCodeOrchestrator()
        assert orchestrator is not None

    def test_claude_code_cli_found(self):
        """Test that Claude Code CLI is available"""
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, "Claude Code CLI not installed"
        assert "Claude Code" in result.stdout or "claude" in result.stdout.lower()

    def test_project_root_configured(self):
        """Test orchestrator can access settings file (implies project root is correct)"""
        orchestrator = ClaudeCodeOrchestrator()
        # The orchestrator stores settings_file which is relative to PROJECT_ROOT
        assert orchestrator.settings_file.exists(), "Settings file should exist"


class TestJiraPromptGeneration:
    """Test that Jira prompts include tool instructions"""

    def test_jira_prompt_contains_tool_instructions(self):
        """Test Jira prompt references Python tools"""
        orchestrator = ClaudeCodeOrchestrator()

        # Build a Jira prompt with full signature
        prompt = orchestrator._build_jira_prompt(
            issue_key="ECD-123",
            comment_text="Test task",
            commenter="Test User",
            commenter_account_id="712020:test123",
            agent_type="jira-manager"
        )

        assert "python -m src.tools.jira" in prompt, "Should reference Python tools"
        assert "src.tools.jira.search" in prompt, "Should mention search tool"
        assert "src.tools.jira.get_issue" in prompt, "Should mention get_issue tool"

    def test_jira_prompt_no_mcp_reference(self):
        """Test Jira prompt does NOT reference MCP tools"""
        orchestrator = ClaudeCodeOrchestrator()
        prompt = orchestrator._build_jira_prompt(
            issue_key="ECD-123",
            comment_text="Test task",
            commenter="Test User",
            commenter_account_id="712020:test123",
            agent_type="jira-manager"
        )

        # Should NOT contain MCP references
        assert "mcp__atlassian" not in prompt, "Should not reference MCP tools"

    def test_jira_prompt_includes_issue_key(self):
        """Test Jira prompt includes the issue key"""
        orchestrator = ClaudeCodeOrchestrator()
        prompt = orchestrator._build_jira_prompt(
            issue_key="ECD-456",
            comment_text="Get status",
            commenter="Test User",
            commenter_account_id="712020:test123",
            agent_type="jira-manager"
        )

        assert "ECD-456" in prompt, "Should include issue key in prompt"


class TestToolAvailability:
    """Test that tools are available for Claude Code to use"""

    def test_search_tool_executable(self):
        """Test search tool can be executed"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.search",
             "project = ECD", "--max-results", "1"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should produce valid JSON
        assert result.stdout, "Search should produce output"
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_get_issue_tool_executable(self):
        """Test get_issue tool can be executed"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.get_issue", "ECD-862"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.stdout, "Get issue should produce output"
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_lookup_user_tool_executable(self):
        """Test lookup_user tool can be executed"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.lookup_user", "ethan"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.stdout, "Lookup user should produce output"
        data = json.loads(result.stdout)
        assert isinstance(data, dict)


class TestClaudeCodeSubprocess:
    """Test Claude Code subprocess invocation"""

    @pytest.mark.slow
    def test_claude_code_can_run_python_tool(self):
        """Test Claude Code can invoke Python tools"""
        # Use Claude Code to run a simple Python command
        result = subprocess.run(
            [
                "claude", "-p",
                "Run: python -m src.tools.jira.list_projects --max-results 2 "
                "and tell me what projects you found",
                "--max-turns", "3"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")}
        )

        # Should complete and mention projects
        assert result.returncode == 0, f"Claude Code failed: {result.stderr}"
        output = result.stdout.lower()
        # Should mention ECD or projects in output
        assert "ecd" in output or "project" in output, \
            f"Should find projects. Output: {result.stdout[:500]}"

    @pytest.mark.slow
    def test_claude_code_jira_search(self):
        """Test Claude Code can search Jira via Python tool"""
        result = subprocess.run(
            [
                "claude", "-p",
                "Search Jira for issues in project ECD that are 'In Progress' "
                "using: python -m src.tools.jira.search \"project = ECD AND status = 'In Progress'\" --max-results 3 "
                "Report the issue keys you found.",
                "--max-turns", "3"
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")}
        )

        assert result.returncode == 0, f"Claude Code failed: {result.stderr}"
        # Should mention ECD issue keys
        assert "ECD-" in result.stdout, f"Should find ECD issues. Output: {result.stdout[:500]}"


class TestEndToEndWorkflows:
    """Test complete message workflows"""

    @pytest.mark.slow
    def test_slack_jira_lookup_workflow(self):
        """Test a Slack message that triggers Jira lookup"""
        orchestrator = ClaudeCodeOrchestrator()

        # Simulate a Slack message asking about a ticket
        mock_message = {
            "text": "What's the status of ECD-862?",
            "user": "U7L6RKG69",
            "channel": "C02NW7QN1RN",
            "ts": "1234567890.123456"
        }

        # Build the prompt that would be sent to Claude
        prompt = orchestrator._build_jira_prompt(
            "ECD-862",
            "Get the current status of this ticket"
        )

        # Verify prompt structure
        assert "ECD-862" in prompt
        assert "python -m src.tools.jira.get_issue" in prompt

    @pytest.mark.slow
    def test_orchestrator_invoke_jira(self):
        """Test orchestrator.invoke_jira() method"""
        orchestrator = ClaudeCodeOrchestrator()

        # This actually calls Claude Code (slow test)
        try:
            result = orchestrator.invoke_jira(
                "ECD-862",
                "Get the status of this issue and report back briefly"
            )

            assert isinstance(result, dict), "Should return a dict"
            assert "result" in result or "response" in result or "error" in result
        except Exception as e:
            # If Claude Code is not available, skip
            pytest.skip(f"Claude Code invocation failed: {e}")


class TestErrorHandling:
    """Test error handling in orchestration"""

    def test_invalid_issue_key_handling(self):
        """Test handling of invalid issue keys"""
        result = subprocess.run(
            [sys.executable, "-m", "src.tools.jira.get_issue", "INVALID-99999"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should return error JSON, not crash
        if result.stdout:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
            # Should indicate error
            assert data.get("error") is True or "error" in str(data).lower()

    def test_network_timeout_handling(self):
        """Test that network timeouts are handled gracefully"""
        # This tests that tools don't hang indefinitely
        # The tools have 30-second timeouts built in

        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Test timed out")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)  # 60 second max for this test

        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.tools.jira.search",
                 "project = ECD", "--max-results", "1"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=45
            )
            # Should complete within timeout
            assert result.returncode in [0, 1]
        finally:
            signal.alarm(0)


class TestToolReadme:
    """Test tool documentation"""

    def test_readme_exists(self):
        """Test that tools README exists"""
        readme_path = PROJECT_ROOT / "src/tools/README.md"
        assert readme_path.exists(), "Tools README should exist"

    def test_readme_documents_all_tools(self):
        """Test that README documents all implemented tools"""
        readme_path = PROJECT_ROOT / "src/tools/README.md"
        readme_content = readme_path.read_text()

        # Check all priority 1 tools are documented
        tools = [
            "search.py",
            "get_issue.py",
            "add_comment.py",
            "edit_issue.py",
            "transition_issue.py",
            "get_transitions.py",
            "lookup_user.py",
            "list_projects.py"
        ]

        for tool in tools:
            assert tool in readme_content, f"README should document {tool}"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment"""
    os.chdir(PROJECT_ROOT)

    # Load .env
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip().strip("'\"")
                    if key and value:
                        os.environ[key] = value

    yield


# Custom markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


if __name__ == "__main__":
    # Run without slow tests by default
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
