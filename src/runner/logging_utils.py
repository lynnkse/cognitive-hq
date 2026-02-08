"""Logging utilities for the agent runner.

Structured logging for agent events, tool calls, and errors.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from src.runner.time_utils import utc_now


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with a consistent format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stderr,
    )


def append_to_transcript(
    transcript_path: Path,
    role: str,
    content: Any,
) -> None:
    """Append a turn to the session transcript JSONL file."""
    entry = {
        "ts": utc_now(),
        "role": role,
        "content": content,
    }
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with open(transcript_path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
