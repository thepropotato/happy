#!/bin/bash
# Run by Happy.app's executable. `launch.sh setup` puts the bundled code in ~/.happy/app and sets it up, printing
# ":: <percent> <text>" lines for the setup window; plain `launch.sh` runs Happy, passing on any arguments.
set -u

resources="$(cd "$(dirname "$0")" && pwd)"
source="$resources/app"
home="${HAPPY_HOME:-$HOME/.happy}"
app="$home/app"
version="$(cat "$source/.app-version")"

# AN APP OPENED FROM FINDER GETS A BARE PATH; THE LOGIN SHELL'S ONE IS WHERE claude, ollama AND uv LIVE.
# shellcheck disable=SC2016
login_path="$("${SHELL:-/bin/zsh}" -lc 'printf %s "$PATH"' 2>/dev/null </dev/null || true)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:${login_path:-/usr/bin:/bin:/usr/sbin:/sbin}"
unset ELECTRON_RUN_AS_NODE

if [ "${1:-}" = "setup" ]; then
  echo "== $(date) setting up Happy $version"
  echo ":: 1 Copying Happy's files"
  mkdir -p "$app"
  # THE CODE IS REPLACED WHOLE, BUT ITS PYTHON ENVIRONMENT STAYS, SO AN UPDATE ONLY FETCHES WHAT CHANGED.
  /usr/bin/rsync -a --delete --exclude ".venv" --exclude ".app-version" "$source/" "$app/" \
    || { echo "::error Happy's files could not be copied into $app."; exit 1; }
  (cd "$app" && HAPPY_NO_START=1 HAPPY_SETUP_PROGRESS=1 PYTHONUNBUFFERED=1 /bin/bash ./setup.sh) || exit 1
  # THE STAMP GOES LAST, SO A SETUP THAT STOPPED PARTWAY RUNS AGAIN ON THE NEXT OPEN.
  cp "$source/.app-version" "$app/.app-version"
  exit 0
fi

python="$app/.venv/bin/python"
if [ ! -x "$python" ] || ! cd "$app"; then
  /usr/bin/osascript -e "display alert \"Happy couldn't start\" message \"Its Python environment is missing. Open Happy again to set it up.\" as critical" >/dev/null 2>&1
  rm -f "$app/.app-version"
  exit 1
fi
# HAPPY REFUSES A SECOND COPY OF ITSELF, SO OPENING THE APP AGAIN WHILE IT RUNS IS HARMLESS.
exec "$python" -m happy run --quiet "$@"
