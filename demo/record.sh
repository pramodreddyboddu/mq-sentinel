#!/usr/bin/env bash
# Record the MQ-Sentinel demo as an asciinema cast.
#
# asciinema casts:
#   - Embed directly in GitHub READMEs (via asciinema.org or self-hosted)
#   - Play in any modern browser (no plugin)
#   - Convert to animated GIF/SVG with svg-term-cli or agg
#   - Are 200x smaller than video files
#
# Output: demo/cast/mq-sentinel.cast

set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAST_FILE="$DEMO_DIR/cast/mq-sentinel.cast"

if ! command -v asciinema >/dev/null 2>&1; then
  echo "asciinema not installed. Install with:"
  echo "  macOS:        brew install asciinema"
  echo "  Linux:        pip install asciinema"
  echo "  Ubuntu/Debian: sudo apt install asciinema"
  exit 1
fi

mkdir -p "$DEMO_DIR/cast"

echo "Recording MQ-Sentinel demo → $CAST_FILE"
echo "When the demo finishes, asciinema saves the cast automatically."
echo

# 100 cols × 32 rows is the GitHub README sweet spot.
# Speed: 'fast' is good for recording; viewers can pause/scrub.
DEMO_SPEED=fast asciinema rec \
  --overwrite \
  --cols 100 \
  --rows 32 \
  --title "MQ-Sentinel — Read-only IBM MQ diagnostics for AI agents" \
  --command "bash $DEMO_DIR/run.sh" \
  "$CAST_FILE"

echo
echo "Cast saved: $CAST_FILE"
echo
echo "Next steps:"
echo "  1. Preview locally:    asciinema play $CAST_FILE"
echo "  2. Upload + share:     asciinema upload $CAST_FILE"
echo "  3. Convert to GIF:     agg $CAST_FILE demo/cast/mq-sentinel.gif"
echo "  4. Convert to SVG:     svg-term --in $CAST_FILE --out demo/cast/mq-sentinel.svg"
echo "  5. Embed in README:    see demo/README.md for the markdown snippet"
