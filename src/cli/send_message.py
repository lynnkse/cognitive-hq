"""CLI tool — send a message to the running agent via Unix socket.

Usage:
    python src/cli/send_message.py "hello agent"
    python src/cli/send_message.py --chat-id mychat "hello"
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python src/cli/send_message.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapters.inbox_client import AgentNotRunningError, send_to_agent


def main():
    parser = argparse.ArgumentParser(
        description="Send a message to the running agent."
    )
    parser.add_argument("text", help="Message text to send", default="hello agent")
    parser.add_argument(
        "--chat-id", default="local-test", help="Chat ID (default: local-test)"
    )
    args = parser.parse_args()

    try:
        ack = send_to_agent(text=args.text, chat_id=args.chat_id)
        print(json.dumps(ack, indent=2))
    except AgentNotRunningError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
