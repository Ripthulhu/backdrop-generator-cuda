#!/bin/bash

# Optional: echo for visibility
echo "Launching backdrop generator with:"
echo "  --length $LENGTH"
echo "  --resolution $RESOLUTION"
echo "  --crf $CRF"
echo "  --timeout $TIMEOUT"
echo "  --interval $INTERVAL"
echo "  FORCE=$FORCE"
echo "  DAEMON=$DAEMON"

# Build args
args=(
  --movies /movies
  --tv /tv
  --length "${LENGTH:-5}"
  --resolution "${RESOLUTION:-720}"
  --crf "${CRF:-28}"
  --timeout "${TIMEOUT:-30}"
  --interval "${INTERVAL:-21600}"
)

# Conditionally add flags
[ "$FORCE" = "true" ] && args+=(--force)
[ "$DAEMON" = "true" ] && args+=(--daemon)

exec python media_theme_processor.py "${args[@]}"
