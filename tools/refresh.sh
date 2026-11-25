#!/bin/sh
# Pull fresh ESPN data and bake it into app.html (the published preview). index.html stays live-fetching.
set -e
cd "$(dirname "$0")/.."
sh build.sh
SNAP="${TMPDIR:-/tmp}/ce_snap.json"
timeout 600 node tools/record.js "$SNAP"
python3 tools/embed.py "$SNAP" app.html
sh build.sh
