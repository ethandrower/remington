"""
Centralized Configuration Management for Autonomous Project Manager

This module provides a single source of truth for all configuration values,
loading them from environment variables with sensible defaults and validation.

Usage:
    from src.config import get_atlassian_config, get_slack_config, get_company_config

    atlassian = get_atlassian_config()
    cloud_id = atlassian['cloud_id']
    jira_url = atlassian['jira_url']
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


def get_atlassian_config() -> Dict[str, str]:
    """
    Get Atlassian/Jira configuration from environment variables

    Returns:
        dict: {
            'cloud_id': str,
            'jira_url': str,
            'project_key': str,
            'bot_account_id': Optional[str]
        }

    Raises:
        ConfigurationError: If required variables are missing
    """
    cloud_id = os.getenv('ATLASSIAN_CLOUD_ID')
    jira_url = os.getenv('JIRA_INSTANCE_URL')
    project_key = os.getenv('ATLASSIAN_PROJECT_KEY')

    # Validate required fields
    if not cloud_id:
        raise ConfigurationError(
            "ATLASSIAN_CLOUD_ID environment variable is required. "
            "Get your Cloud ID from https://admin.atlassian.com/ (in the URL)"
        )

    if not jira_url:
        raise ConfigurationError(
            "JIRA_INSTANCE_URL environment variable is required. "
            "Format: https://your-company.atlassian.net"
        )

    if not project_key:
        raise ConfigurationError(
            "ATLASSIAN_PROJECT_KEY environment variable is required. "
            "This is your main Jira project key (e.g., 'PROJ', 'DEV', 'ENG')"
        )

    # Ensure jira_url doesn't have trailing slash
    jira_url = jira_url.rstrip('/')

    return {
        'cloud_id': cloud_id,
        'jira_url': jira_url,
        'project_key': project_key,
        'bot_account_id': os.getenv('PM_BOT_ACCOUNT_ID'),  # Optional
    }


def get_slack_config() -> Dict[str, str]:
    """
    Get Slack configuration from environment variables

    Returns:
        dict: {
            'bot_token': str,
            'bot_user_id': str,
            'channel_standup': str,
            'channel_logs': str,
        }

    Raises:
        ConfigurationError: If required variables are missing
    """
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    bot_user_id = os.getenv('SLACK_BOT_USER_ID')
    channel_standup = os.getenv('SLACK_CHANNEL_STANDUP')
    channel_logs = os.getenv('SLACK_PM_AGENT_LOG_CHANNEL')

    if not bot_token:
        raise ConfigurationError(
            "SLACK_BOT_TOKEN environment variable is required. "
            "Get it from https://api.slack.com/apps > Your App > OAuth & Permissions"
        )

    if not bot_user_id:
        raise ConfigurationError(
            "SLACK_BOT_USER_ID environment variable is required. "
            "Get it using client.auth_test() or from Slack app settings"
        )

    return {
        'bot_token': bot_token,
        'bot_user_id': bot_user_id,
        'channel_standup': channel_standup or '',
        'channel_logs': channel_logs or '',
    }


def get_company_config() -> Dict[str, str]:
    """
    Get company-specific configuration

    Returns:
        dict: {
            'name': str,
            'timezone': str,
            'holidays': List[str]
        }
    """
    return {
        'name': os.getenv('COMPANY_NAME', 'YourCompany'),
        'timezone': os.getenv('BUSINESS_TIMEZONE', 'America/New_York'),
        'holidays': os.getenv('COMPANY_HOLIDAYS', '').split(',') if os.getenv('COMPANY_HOLIDAYS') else [],
    }


def get_repository_paths() -> Dict[str, Optional[str]]:
    """
    Get repository paths for multi-repo monitoring

    Returns:
        dict: {
            'main': Optional[str],
            'secondary': Optional[str],
            'pm_agent': Optional[str]
        }
    """
    return {
        'main': os.getenv('MAIN_REPO_PATH'),
        'secondary': os.getenv('SECONDARY_REPO_PATH'),
        'pm_agent': os.getenv('PM_AGENT_PATH'),
    }


def get_team_roster() -> Optional[List[Dict[str, str]]]:
    """
    Get team roster configuration

    Returns:
        List of dicts with 'name' and 'account_id' keys, or None if not configured

    Example:
        [
            {'name': 'John Doe', 'account_id': 'accountId:123abc'},
            {'name': 'Jane Smith', 'account_id': 'accountId:456def'}
        ]
    """
    names = os.getenv('TEAM_MEMBER_NAMES', '')
    ids = os.getenv('TEAM_MEMBER_IDS', '')

    if not names or not ids:
        return None

    name_list = [n.strip() for n in names.split(',')]
    id_list = [i.strip() for i in ids.split(',')]

    if len(name_list) != len(id_list):
        raise ConfigurationError(
            "TEAM_MEMBER_NAMES and TEAM_MEMBER_IDS must have the same number of entries"
        )

    return [
        {'name': name, 'account_id': account_id}
        for name, account_id in zip(name_list, id_list)
    ]


def get_sla_config() -> Dict[str, any]:
    """
    Get SLA configuration

    Returns:
        dict: {
            'business_hours_start': int,
            'business_hours_end': int,
            'timezone': str
        }
    """
    return {
        'business_hours_start': int(os.getenv('BUSINESS_HOURS_START', '9')),
        'business_hours_end': int(os.getenv('BUSINESS_HOURS_END', '17')),
        'timezone': os.getenv('BUSINESS_TIMEZONE', 'America/New_York'),
    }


def get_workflow_config() -> Dict[str, bool]:
    """
    Get workflow configuration flags

    Returns:
        dict: {
            'dry_run': bool,
            'verbose_logging': bool
        }
    """
    return {
        'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
        'verbose_logging': os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true',
    }


def get_anthropic_api_key() -> str:
    """
    Get Anthropic API key

    Returns:
        str: API key

    Raises:
        ConfigurationError: If API key is missing
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        raise ConfigurationError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Get your API key from https://console.anthropic.com/"
        )

    return api_key


def validate_all_config(require_slack: bool = False, require_repos: bool = False) -> bool:
    """
    Validate all required configuration is present

    Args:
        require_slack: Whether Slack config is required (default: False)
        require_repos: Whether repository paths are required (default: False)

    Returns:
        bool: True if all required config is valid

    Raises:
        ConfigurationError: If any required config is missing
    """
    # Always required
    get_anthropic_api_key()
    get_atlassian_config()

    # Conditionally required
    if require_slack:
        get_slack_config()

    if require_repos:
        repos = get_repository_paths()
        if not repos['main']:
            raise ConfigurationError(
                "MAIN_REPO_PATH environment variable is required for repository monitoring"
            )

    return True


# Convenience functions for common use cases
def get_jira_base_url() -> str:
    """Get the Jira base URL (convenience method)"""
    config = get_atlassian_config()
    return config['jira_url']


def get_cloud_id() -> str:
    """Get the Atlassian Cloud ID (convenience method)"""
    config = get_atlassian_config()
    return config['cloud_id']


def get_project_key() -> str:
    """Get the primary Jira project key (convenience method)"""
    config = get_atlassian_config()
    return config['project_key']


def is_dry_run() -> bool:
    """Check if dry-run mode is enabled (convenience method)"""
    config = get_workflow_config()
    return config['dry_run']


if __name__ == '__main__':
    """
    Run this file directly to test configuration:
        python src/config.py
    """
    print("🔍 Validating Configuration...\n")

    try:
        # Test Anthropic
        print("✅ Anthropic API Key: ", get_anthropic_api_key()[:20] + "...")

        # Test Atlassian
        atlassian = get_atlassian_config()
        print(f"✅ Atlassian Cloud ID: {atlassian['cloud_id']}")
        print(f"✅ Jira URL: {atlassian['jira_url']}")
        print(f"✅ Project Key: {atlassian['project_key']}")

        # Test Company
        company = get_company_config()
        print(f"✅ Company Name: {company['name']}")

        # Test Slack (optional)
        try:
            slack = get_slack_config()
            print(f"✅ Slack Bot Token: {slack['bot_token'][:20]}...")
        except ConfigurationError as e:
            print(f"ℹ️  Slack Config (optional): Not configured - {str(e)}")

        # Test Team Roster (optional)
        roster = get_team_roster()
        if roster:
            print(f"✅ Team Roster: {len(roster)} members configured")
        else:
            print("ℹ️  Team Roster: Not configured (optional)")

        # Test Repository Paths (optional)
        repos = get_repository_paths()
        if repos['main']:
            print(f"✅ Main Repo Path: {repos['main']}")
        else:
            print("ℹ️  Repository Paths: Not configured (optional)")

        # Test Workflow
        workflow = get_workflow_config()
        print(f"ℹ️  Dry Run Mode: {workflow['dry_run']}")
        print(f"ℹ️  Verbose Logging: {workflow['verbose_logging']}")

        print("\n✅ All required configuration is valid!")

    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {str(e)}")
        print("\nPlease check your .env file and ensure all required variables are set.")
        print("See .env.example for reference.")
        exit(1)