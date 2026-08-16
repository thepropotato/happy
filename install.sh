#!/bin/sh
# THE ONE LINE. GETS HAPPY, GETS EVERYTHING HE NEEDS, AND LEAVES AN APP YOU CAN CLICK:
#
#     curl -fsSL https://raw.githubusercontent.com/thepropotato/happy/main/install.sh | sh
#
# Everything it installs goes in one folder, and taking him off again is deleting it.

set -eu

REPO="https://github.com/thepropotato/happy.git"
HOME_DIR="${HAPPY_HOME:-$HOME/.happy}"

say() {
    printf '%s\n' "$1"
}

need() {
    command -v "$1" >/dev/null 2>&1
}

# GIT IS THE ONE THING THAT HAS TO BE HERE ALREADY, BECAUSE IT IS WHAT FETCHES THE REST.
if ! need git; then
    say "Happy is fetched with git, and there is none here."
    say ""

    if [ "$(uname -s)" = "Darwin" ]; then
        say "macOS will install it for you if you run:"
        say "    xcode-select --install"
    else
        say "Get it with, for example:"
        say "    sudo apt-get install -y git"
    fi

    exit 1
fi

if [ -d "$HOME_DIR/.git" ]; then
    say "Happy is already in $HOME_DIR. Bringing him up to date."
    git -C "$HOME_DIR" pull --ff-only --quiet || say "Could not update, going on with what is there."
else
    say "Putting Happy in $HOME_DIR"
    git clone --quiet "$REPO" "$HOME_DIR"
fi

cd "$HOME_DIR"

chmod +x setup.sh 2>/dev/null || true

# setup.sh FINDS A PYTHON AND HANDS OVER TO bones, WHICH DOES ALL THE ACTUAL WORK.
exec ./setup.sh "$@"
