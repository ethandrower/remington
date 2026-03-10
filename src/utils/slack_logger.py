#!/usr/bin/env python3
"""
Centralized Slack Logging Utility

Posts heartbeats, activity logs, errors, and reports to #pm-agent-logs channel.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackLogger:
    """Centralized logging to Slack #pm-agent-logs channel"""

    def __init__(self):
        from src.utils.channel_config import get_channel
        self.token = os.getenv("SLACK_BOT_TOKEN")
        self.log_channel = get_channel("pm_logs")

        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN not set in environment")

        if not self.log_channel:
            print("⚠️  PM logs channel not configured — configure 'PM Agent Logs' in dashboard Settings")
            self.client = None
            return

        self.client = WebClient(token=self.token)
        self._verify_channel()

    def _is_configured(self) -> bool:
        return bool(self.client and self.log_channel)

    def _verify_channel(self):
        """Verify the logging channel exists and bot has access"""
        try:
            response = self.client.conversations_info(channel=self.log_channel)
            print(f"✅ Slack logging channel verified: #{response['channel']['name']}")
        except SlackApiError as e:
            print(f"⚠️ Warning: Cannot access Slack logging channel {self.log_channel}: {e.response['error']}")

    def post_heartbeat(self, metrics: Dict[str, Any]) -> bool:
        """
        Post hourly heartbeat with metrics

        Args:
            metrics: Dict containing:
                - status: "operational" | "degraded" | "error"
                - jira_comments: int
                - pr_reviews: int
                - sla_violations: int
                - uptime_percent: float
                - errors: list of error messages (optional)
        """
        status_emoji = {
            "operational": "✅",
            "degraded": "⚠️",
            "error": "❌"
        }

        emoji = status_emoji.get(metrics.get("status", "operational"), "🤖")
        now = datetime.now().strftime("%I:%M %p CST")

        message = f"""{emoji} **PM Agent Heartbeat** - {now}
━━━━━━━━━━━━━━━━━━━━━━━

**Status:** {metrics.get('status', 'operational').title()}

📊 **Last hour activity:**
  • {metrics.get('jira_comments', 0)} Jira comments monitored
  • {metrics.get('pr_reviews', 0)} PR reviews completed
  • {metrics.get('sla_violations', 0)} SLA violations detected

⚡ **Service uptime:** {metrics.get('uptime_percent', 100.0):.1f}%
"""

        # Add errors if present
        if metrics.get('errors'):
            message += "\n⚠️ **Recent errors:**\n"
            for error in metrics['errors'][:3]:  # Show max 3 errors
                message += f"  • {error}\n"

        return self._post_message(message)

    def post_daily_standup(self, report: str, mention_user_id: Optional[str] = None) -> bool:
        """
        Post daily standup report

        Args:
            report: Formatted report text
            mention_user_id: Slack user ID to mention (e.g., for Ethan)
        """
        message = "📊 **Daily Standup Report** - " + datetime.now().strftime("%b %d, %Y") + "\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        if mention_user_id:
            message += f"<@{mention_user_id}>\n\n"

        message += report

        return self._post_message(message)

    def post_weekly_summary(self, report: str) -> bool:
        """Post weekly summary report"""
        message = "📊 **Weekly PM Agent Report**\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += report

        return self._post_message(message)

    def post_error(self, service: str, error_msg: str, details: Optional[str] = None) -> bool:
        """
        Post error alert

        Args:
            service: Name of service/component (e.g., "Bitbucket Monitor")
            error_msg: Error message
            details: Optional additional details
        """
        now = datetime.now().strftime("%I:%M %p CST")

        message = f"""⚠️ **PM Agent Error**
━━━━━━━━━━━━━━━━━
**Service:** {service}
**Error:** {error_msg}
**Time:** {now}
"""

        if details:
            message += f"\n**Details:**\n{details}\n"

        return self._post_message(message)

    def post_warning(self, service: str, warning_msg: str, action: Optional[str] = None) -> bool:
        """
        Post warning (non-critical issue)

        Args:
            service: Name of service/component
            warning_msg: Warning message
            action: Action being taken (optional)
        """
        now = datetime.now().strftime("%I:%M %p CST")

        message = f"""⚠️ **PM Agent Warning**
━━━━━━━━━━━━━━━━━
**Service:** {service}
**Issue:** {warning_msg}
"""

        if action:
            message += f"**Action:** {action}\n"

        message += f"**Time:** {now}\n"

        return self._post_message(message)

    def post_activity(self, activity_type: str, description: str, link: Optional[str] = None) -> bool:
        """
        Post activity log (successful action)

        Args:
            activity_type: Type of activity (e.g., "PR Review", "Jira Comment")
            description: Description of what was done
            link: Optional link to the item
        """
        emoji_map = {
            "PR Review": "🔍",
            "Jira Comment": "💬",
            "SLA Escalation": "🚨",
            "Standup Report": "📊",
            "Developer Audit": "👤"
        }

        emoji = emoji_map.get(activity_type, "✅")

        message = f"{emoji} **{activity_type}**\n{description}"

        if link:
            message += f"\n🔗 {link}"

        return self._post_message(message)

    def _post_message(self, text: str) -> bool:
        """
        Internal method to post message to Slack

        Args:
            text: Message text (supports markdown)

        Returns:
            True if successful, False otherwise
        """
        if not self._is_configured():
            return False
        try:
            response = self.client.chat_postMessage(
                channel=self.log_channel,
                text=text,
                mrkdwn=True,
                unfurl_links=False,
                unfurl_media=False
            )
            return response["ok"]
        except SlackApiError as e:
            print(f"❌ Failed to post to Slack: {e.response['error']}")
            print(f"   Message: {text[:100]}...")
            return False
        except Exception as e:
            print(f"❌ Unexpected error posting to Slack: {e}")
            return False


# Singleton instance
_logger_instance = None

def get_slack_logger() -> SlackLogger:
    """Get singleton SlackLogger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SlackLogger()
    return _logger_instance
