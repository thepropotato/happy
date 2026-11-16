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

# AGENT-BROWSER IS ONE FILE PER SYSTEM ON ITS RELEASES, SO NEITHER HOMEBREW NOR NODE IS NEEDED.
AGENT_BROWSER=v0.43.0
if ! command -v agent-browser >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/agent-browser" ]; then
  echo "Getting agent-browser, which lets Happy work inside pages in your own Chrome…"
  case "$(uname -m)" in arm64|aarch64) arch=arm64 ;; *) arch=x64 ;; esac
  case "$(uname -s)" in Darwin) os=darwin ;; *) os=linux ;; esac
  mkdir -p "$HOME/.local/bin"
  if curl -fsSL -o "$HOME/.local/bin/agent-browser" \
      "https://github.com/vercel-labs/agent-browser/releases/download/$AGENT_BROWSER/agent-browser-$os-$arch"; then
    chmod +x "$HOME/.local/bin/agent-browser"
  else
    rm -f "$HOME/.local/bin/agent-browser"
    echo "agent-browser could not be downloaded; pages are worked through accessibility instead, and setup will try again next time."
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

# THE MAC APP RUNS SETUP ITSELF AND STARTS HAPPY ITS OWN WAY, SO IT ASKS FOR SETUP ALONE.
[ -n "${HAPPY_NO_START:-}" ] || uv run happy start --settings
