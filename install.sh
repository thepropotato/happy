#!/bin/sh
# Installs or updates Happy in one line: curl -fsSL https://raw.githubusercontent.com/thepropotato/happy/main/install.sh | sh
set -eu

# EVERYTHING RUNS FROM main, SO A DOWNLOAD CUT OFF HALFWAY RUNS NOTHING.
main() {
  repo="https://github.com/thepropotato/happy"
  dir="${HAPPY_DIR:-$HOME/.happy/app}"

  if [ -d "$dir/.git" ] && has_git; then
    echo "Updating Happy in $dir..."
    git -C "$dir" pull --ff-only --quiet
  elif [ ! -e "$dir" ] && has_git; then
    echo "Getting Happy..."
    mkdir -p "$(dirname "$dir")"
    git clone --depth 1 --quiet "$repo.git" "$dir"
  else
    echo "Getting Happy..."
    mkdir -p "$dir"
    curl -fsSL "$repo/archive/refs/heads/main.tar.gz" | tar -xz --strip-components=1 -C "$dir"
  fi

  cd "$dir"
  exec bash ./setup.sh
}

# ON A MAC WITHOUT THE DEVELOPER TOOLS, git IS A STUB THAT ONLY OPENS AN INSTALL DIALOG.
has_git() {
  command -v git >/dev/null 2>&1 || return 1
  [ "$(uname -s)" != "Darwin" ] || xcode-select -p >/dev/null 2>&1
}

main "$@"
