#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
LOG_FILE="$SCRIPT_DIR/LOG.md"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "ERROR: LOG.md not found at $LOG_FILE" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "ERROR: claude-log requires a message" >&2
  exit 1
fi

{
  echo "### $(date)"
  echo "$*"
  echo
} >> "$LOG_FILE"
