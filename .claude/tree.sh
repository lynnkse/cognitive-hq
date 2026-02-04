#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Follow symlinks (-l) so linked repos are expanded.
# Prune noisy / huge dirs so TREE.txt stays useful for reasoning.
tree -a -l -L 5 \
  -I ".git|build|devel|install|logs|log|__pycache__|\.venv|\.mypy_cache|\.pytest_cache|\.cache|node_modules|\.idea|\.vscode|cmake-build-.*|results" \
  "$REPO_ROOT" > "$SCRIPT_DIR/TREE.txt"

echo "TREE.txt updated at $SCRIPT_DIR/TREE.txt"
