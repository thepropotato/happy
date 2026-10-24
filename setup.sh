#!/usr/bin/env bash
# Sets Happy up on macOS or Linux: Python environment, speech models, brain, and a `happy` command.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (the Python package manager Happy uses)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v claude >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/claude" ]; then
  echo "Installing Claude Code, which keeps your list of MCP services (no subscription needed for that)…"
  curl -fsSL https://claude.ai/install.sh | bash
fi

uv sync --quiet
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/.venv/bin/happy" "$HOME/.local/bin/happy"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "Add ~/.local/bin to your PATH to run 'happy' from anywhere." ;;
esac

uv run happy setup
