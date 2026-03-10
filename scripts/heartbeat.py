#!/usr/bin/env python3
"""
Heartbeat script — posts a status ping to Slack #pm-agent-logs.
Called hourly by clock.py during business hours.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.utils.slack_logger import get_slack_logger


def main():
    try:
        logger = get_slack_logger()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.post_activity(
            "Heartbeat",
            f"PM Agent is alive and running | {now}",
        )
        print(f"✅ Heartbeat posted at {now}")
    except Exception as e:
        print(f"⚠️  Heartbeat failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
