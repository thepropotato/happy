#!/usr/bin/env bash
# Sets Happy up on macOS or Linux: Python environment, speech models, brain, and a `happy` command.
set -euo pipefail
cd "$(dirname "$0")"

# THE MAC APP'S SETUP WINDOW READS ":: <percent> <text>" LINES; A PERSON IN A TERMINAL JUST SEES THE TEXT.
step() {
  if [ -n "${HAPPY_SETUP_PROGRESS:-}" ]; then echo ":: $1 $2"; else echo "$2"; fi
}

if ! command -v uv >/dev/null 2>&1; then
  step 2 "Installing uv, the Python package manager Happy uses"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v claude >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/claude" ]; then
  step 5 "Installing Claude Code, which keeps your list of MCP services (no subscription needed for that)"
  curl -fsSL https://claude.ai/install.sh | bash || echo "Claude Code could not be installed right now. Happy works without it; adding MCP services needs it, and setup will try again next time."
fi

# AGENT-BROWSER IS ONE FILE PER SYSTEM ON ITS RELEASES, SO NEITHER HOMEBREW NOR NODE IS NEEDED.
AGENT_BROWSER=v0.43.0
if ! command -v agent-browser >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/agent-browser" ]; then
  step 10 "Getting agent-browser, which lets Happy work inside pages in your own Chrome"
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

step 14 "Installing Happy's Python packages (the longest part)"
if ! uv sync --quiet; then
  echo "::error Installing Happy's Python packages failed. Check the internet connection and try again."
  exit 1
fi
mkdir -p "$HOME/.local/bin"
ln -sf "$PWD/.venv/bin/happy" "$HOME/.local/bin/happy"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "Add ~/.local/bin to your PATH to run 'happy' from anywhere." ;;
esac

# THE SPEECH MODELS AND THE VOICE COME NOW, SO HAPPY'S FIRST WINDOW CAN LISTEN AND TALK STRAIGHT AWAY.
.venv/bin/python -m happy prepare

# THE MAC APP RUNS SETUP ITSELF AND STARTS HAPPY ITS OWN WAY, SO IT ASKS FOR SETUP ALONE.
[ -n "${HAPPY_NO_START:-}" ] || uv run happy start --settings
