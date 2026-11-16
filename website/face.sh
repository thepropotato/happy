#!/usr/bin/env bash
# Copies the app's own mouth and background light, so the site's Happy is the app's Happy.
set -euo pipefail
cd "$(dirname "$0")"
web=../happy/ui/web
cp "$web/aurora.js" "$web/smile/shapes.js" "$web/smile/drawing.js" "$web/smile/mouth.js" "$web/smile/life.js" face/
