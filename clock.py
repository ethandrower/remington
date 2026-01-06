#!/usr/bin/env python3
"""
Heroku Clock Process - Scheduled Task Runner
Runs the daily standup and periodic SLA checks.
"""

import os
import sys
import schedule
import time
import logging
from datetime import datetime
import pytz
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TIMEZONE = os.getenv('BUSINESS_TIMEZONE', 'America/New_York')
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'


def run_command(command):
    """Run a command and log output."""
    logger.info(f"Running command: {command}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.stdout:
            logger.info(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            logger.error(f"STDERR:\n{result.stderr}")

        if result.returncode != 0:
            logger.error(f"Command failed with exit code {result.returncode}")
            # Send error notification
            notify_error(command, result.stderr)
        else:
            logger.info(f"Command completed successfully")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after 10 minutes")
        notify_error(command, "Command timed out")
        return False

    except Exception as e:
        logger.error(f"Error running command: {e}")
        notify_error(command, str(e))
        return False


def notify_error(command, error_message):
    """Send error notification to Slack/Email."""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if slack_token:
            # TODO: Implement Slack error notification
            logger.info(f"Would send Slack notification about error in: {command}")
    except Exception as e:
        logger.error(f"Failed to send error notification: {e}")


def daily_standup():
    """Run daily standup workflow."""
    logger.info("=" * 60)
    logger.info("Starting Daily Standup Workflow")
    logger.info("=" * 60)

    # Get current time in ET
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if DRY_RUN:
        logger.info("DRY_RUN mode - skipping actual execution")
        return

    success = run_command("python run_agent.py standup --notify-ethan")

    if success:
        logger.info("✅ Daily standup completed successfully")
    else:
        logger.error("❌ Daily standup failed")


def hourly_sla_check():
    """Run hourly SLA monitoring."""
    logger.info("-" * 60)
    logger.info("Starting Hourly SLA Check")
    logger.info("-" * 60)

    if DRY_RUN:
        logger.info("DRY_RUN mode - skipping actual execution")
        return

    success = run_command("python run_agent.py sla-check")

    if success:
        logger.info("✅ SLA check completed")
    else:
        logger.error("❌ SLA check failed")


def send_slack_heartbeat():
    """Send heartbeat status to Slack channel using new heartbeat script."""
    logger.info("-" * 60)
    logger.info("Sending Hourly Heartbeat to Slack")
    logger.info("-" * 60)

    if DRY_RUN:
        logger.info("DRY_RUN mode - skipping actual execution")
        return

    # Only send heartbeat during business hours (9am-5pm weekdays)
    if not is_business_hours():
        logger.info("Outside business hours - skipping heartbeat")
        return

    success = run_command("python scripts/heartbeat.py")

    if success:
        logger.info("✅ Heartbeat posted to Slack")
    else:
        logger.error("❌ Heartbeat posting failed")


# Global start time for uptime calculation
START_TIME = None


def get_uptime():
    """Calculate uptime since process started."""
    global START_TIME
    if START_TIME is None:
        return "Just started"

    uptime_seconds = (datetime.now() - START_TIME).total_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def health_check():
    """Periodic health check to ensure worker is alive."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    logger.info(f"💚 Health check OK - {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def is_business_hours():
    """Check if current time is within business hours."""
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    # Check if weekday (Monday = 0, Sunday = 6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False

    # Check if within business hours (9 AM - 5 PM ET)
    start_hour = int(os.getenv('BUSINESS_HOURS_START', '9'))
    end_hour = int(os.getenv('BUSINESS_HOURS_END', '17'))

    if now.hour < start_hour or now.hour >= end_hour:
        return False

    return True


def main():
    """Main scheduler loop."""
    global START_TIME
    START_TIME = datetime.now()

    logger.info("=" * 60)
    logger.info("CiteMed PM Agent Clock Process Starting")
    logger.info("=" * 60)
    logger.info(f"Timezone: {TIMEZONE}")
    logger.info(f"DRY_RUN: {DRY_RUN}")
    logger.info(f"Python: {sys.version}")
    logger.info("=" * 60)

    # Schedule daily standup at 9:00 AM ET (weekdays only)
    schedule.every().monday.at("09:00").do(daily_standup)
    schedule.every().tuesday.at("09:00").do(daily_standup)
    schedule.every().wednesday.at("09:00").do(daily_standup)
    schedule.every().thursday.at("09:00").do(daily_standup)
    schedule.every().friday.at("09:00").do(daily_standup)

    # Schedule SLA checks every hour during business hours
    schedule.every().hour.do(lambda: hourly_sla_check() if is_business_hours() else None)

    # Health check every 10 minutes (local logging)
    schedule.every(10).minutes.do(health_check)

    # Slack heartbeat every hour
    schedule.every().hour.do(send_slack_heartbeat)

    logger.info("✅ Scheduler configured")
    logger.info("Next standup: " + str(schedule.next_run()))

    # Run immediately if requested
    if os.getenv('RUN_IMMEDIATE', 'false').lower() == 'true':
        logger.info("RUN_IMMEDIATE=true, running standup now...")
        daily_standup()

    # Main loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("Shutting down clock process...")
            logger.info("=" * 60)
            break

        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            time.sleep(60)  # Wait before retrying


if __name__ == '__main__':
    main()
