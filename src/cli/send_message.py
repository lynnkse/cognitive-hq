"""CLI tool — enqueue a message to the Telegram emulator inbox.

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

from src.adapters.telegram_emulator import TelegramEmulator


def main():
    parser = argparse.ArgumentParser(
        description="Send a message to the Telegram emulator inbox."
    )
    parser.add_argument("text", help="Message text to send")
    parser.add_argument(
        "--chat-id", default="local-test", help="Chat ID (default: local-test)"
    )
    args = parser.parse_args()

    emulator = TelegramEmulator()
    record = emulator.enqueue_message(text=args.text, chat_id=args.chat_id)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
