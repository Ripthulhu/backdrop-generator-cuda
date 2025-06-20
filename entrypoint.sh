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
echo "  NO_AUDIO=$NO_AUDIO"
echo "  FFMPEG_EXTRA=$FFMPEG_EXTRA"

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
[ "$NO_AUDIO" = "true" ] && args+=(--no-audio)

# Add custom FFmpeg parameters if provided
[ -n "$FFMPEG_EXTRA" ] && args+=(--ffmpeg-extra "$FFMPEG_EXTRA")

exec python media_theme_processor.py "${args[@]}"