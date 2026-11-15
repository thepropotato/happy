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
  curl -fsSL https://claude.ai/install.sh | bash || echo "Claude Code could not be installed right now. Happy works without it; adding MCP services needs it, and setup will try again next time."
fi

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "Installing agent-browser, which lets Happy work inside pages in your own Chrome…"
  if command -v brew >/dev/null 2>&1; then
    brew install --quiet agent-browser || echo "agent-browser could not be installed; pages are worked through accessibility instead."
  elif command -v npm >/dev/null 2>&1; then
    npm install -g --silent agent-browser || echo "agent-browser could not be installed; pages are worked through accessibility instead."
  else
    echo "agent-browser needs Homebrew or Node; pages are worked through accessibility instead."
  fi
fi

if ! uv sync --quiet; then
  echo "Installing Happy's Python packages failed. Check the internet connection and run ./setup.sh again."
  exit 1
fi
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/.venv/bin/happy" "$HOME/.local/bin/happy"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "Add ~/.local/bin to your PATH to run 'happy' from anywhere." ;;
esac

uv run happy start --settings
