#!/bin/bash
# Happy.app's executable: puts the bundled code in ~/.happy/app, sets it up the first time and after an update, then runs Happy.
set -u

bundle="$(cd "$(dirname "$0")/.." && pwd)"
source="$bundle/Resources/app"
home="${HAPPY_HOME:-$HOME/.happy}"
app="$home/app"
log="$home/install.log"
version="$(cat "$source/.app-version")"

# AN APP OPENED FROM FINDER GETS A BARE PATH; THE LOGIN SHELL'S ONE IS WHERE claude, ollama AND uv LIVE.
# shellcheck disable=SC2016
login_path="$("${SHELL:-/bin/zsh}" -lc 'printf %s "$PATH"' 2>/dev/null || true)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:${login_path:-/usr/bin:/bin:/usr/sbin:/sbin}"
unset ELECTRON_RUN_AS_NODE

say() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"Happy\"" >/dev/null 2>&1 || true
}

trouble() {
  /usr/bin/osascript -e "display alert \"Happy couldn't finish setting up\" message \"$1 The details are in $log.\" as critical" >/dev/null 2>&1 || true
  exit 1
}

mkdir -p "$home"
first=""
if [ "$(cat "$app/.app-version" 2>/dev/null)" != "$version" ]; then
  [ -d "$app/.venv" ] || first="--settings"
  say "Getting Happy ready. The first time takes a few minutes."
  {
    echo "== $(date) setting up Happy $version"
    mkdir -p "$app"
    # THE CODE IS REPLACED WHOLE, BUT ITS PYTHON ENVIRONMENT STAYS, SO AN UPDATE ONLY FETCHES WHAT CHANGED.
    /usr/bin/rsync -a --delete --exclude ".venv" --exclude ".app-version" "$source/" "$app/"
  } >>"$log" 2>&1 || trouble "Its files could not be copied."
  (cd "$app" && HAPPY_NO_START=1 /bin/bash ./setup.sh) >>"$log" 2>&1 || trouble "Setup stopped partway."
  cp "$source/.app-version" "$app/.app-version"
fi

python="$app/.venv/bin/python"
[ -x "$python" ] || trouble "Its Python environment is missing."
cd "$app" || trouble "Its folder could not be opened."
# HAPPY REFUSES A SECOND COPY OF ITSELF, SO OPENING THE APP AGAIN WHILE IT RUNS IS HARMLESS.
exec "$python" -m happy run --quiet $first
