#!/bin/sh
# GET THIS MACHINE READY FOR HAPPY. EVERYTHING IT DOES IS IN bones/, WHICH NEEDS ONLY THE
# STANDARD LIBRARY, SO THE ONLY JOB HERE IS FINDING A PYTHON NEW ENOUGH TO RUN IT.

set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$HERE"

LEAST_MINOR=11

# THE NEWEST FIRST, SO A MACHINE WITH SEVERAL DOES NOT SETTLE FOR ITS OLDEST.
CANDIDATES="python3.14 python3.13 python3.12 python3.11 python3 python"

new_enough() {
    "$1" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, $LEAST_MINOR) else 1)" \
        >/dev/null 2>&1
}

find_python() {
    for name in $CANDIDATES; do
        if command -v "$name" >/dev/null 2>&1 && new_enough "$name"; then
            printf '%s' "$name"
            return 0
        fi
    done

    return 1
}

if ! PYTHON=$(find_python); then
    echo "Happy needs Python 3.$LEAST_MINOR or newer, and there is none here."
    echo

    if [ "$(uname -s)" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            echo "Get it with:"
            echo "    brew install python@3.13"
        else
            echo "Get Homebrew first:"
            echo '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
            echo
            echo "then:"
            echo "    brew install python@3.13"
        fi
    else
        echo "Get it from your package manager, for example:"
        echo "    sudo apt-get install -y python3 python3-venv"
    fi

    exit 1
fi

exec "$PYTHON" -m bones "$@"
