"""Entry point — starts the always-on agent runner.

Usage:
    python src/cli/run_agent.py
    python src/cli/run_agent.py --model sonnet --poll-interval 5
"""

import argparse
import sys
from pathlib import Path

# Allow running as `python src/cli/run_agent.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.runner.agent_runner import AgentRunner
from src.runner.cloudcode_bridge import CloudCodeBridge
from src.runner.logging_utils import setup_logging


def main():
    parser = argparse.ArgumentParser(description="Start the always-on agent runner.")
    parser.add_argument("--model", default="haiku", help="CloudCode model (default: haiku)")
    parser.add_argument("--timeout", type=int, default=30, help="CloudCode timeout in seconds (default: 30)")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Inbox poll interval in seconds (default: 2.0)")
    parser.add_argument("--log-level", default="INFO", help="Log level (default: INFO)")
    args = parser.parse_args()

    setup_logging(level=args.log_level)

    telegram = TelegramEmulator()
    memory = MemoryEmulator()
    bridge = CloudCodeBridge(model=args.model, timeout_seconds=args.timeout)

    runner = AgentRunner(
        telegram=telegram,
        memory=memory,
        bridge=bridge,
        poll_interval=args.poll_interval,
    )

    print(f"Agent runner starting (model={args.model}, poll={args.poll_interval}s)")
    print("Send messages with: python src/cli/send_message.py \"your message\"")
    print("Press Ctrl+C to stop.")
    runner.run()


if __name__ == "__main__":
    main()
