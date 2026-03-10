#!/usr/bin/env python3
"""
Interactive test for the LangGraph conversation agent.

Run this directly to test the agent in your terminal before wiring it
into the Slack polling loop.

    python -m src.agents.test_agent

Type messages as if you were @mentioning Remington in Slack.
The agent remembers context within a session (same thread_ts = same thread).
Type 'new' to start a fresh thread, 'quit' to exit.
"""

import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.conversation_agent import run_agent

THREAD_TS = str(time.time())  # Unique thread for this test session


def main():
    print("\n" + "=" * 60)
    print(" 🤖 Remington Agent — Interactive Test ".center(60))
    print("=" * 60)
    print(f"Thread ID: {THREAD_TS}")
    print("Commands: 'new' = new thread, 'quit' = exit")
    print("=" * 60 + "\n")

    thread_ts = THREAD_TS
    author = "Test User"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            break

        if user_input.lower() == "new":
            thread_ts = str(time.time())
            print(f"\n[New thread started: {thread_ts}]\n")
            continue

        print("\nRemington: ", end="", flush=True)
        try:
            response = run_agent(
                thread_ts=thread_ts,
                channel="C_TEST",
                author=author,
                message=user_input,
            )
            print(response)
        except Exception as e:
            print(f"[Error: {e}]")
            import traceback
            traceback.print_exc()

        print()


if __name__ == "__main__":
    main()
