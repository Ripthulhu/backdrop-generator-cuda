#!/usr/bin/env bash
set -euo pipefail

echo "Launching backdrop generator with:"
echo "  --length      ${LENGTH:-5}"
echo "  --resolution  ${RESOLUTION:-720}"
echo "  --crf         ${CRF:-28}"
echo "  --timeout     ${TIMEOUT:-30}"
echo "  --interval    ${INTERVAL:-21600}"
echo "  FORCE         ${FORCE:-false}"
echo "  DAEMON        ${DAEMON:-false}"
echo "  NO_AUDIO      ${NO_AUDIO:-false}"
echo "  ANIME_PATH    ${ANIME_PATH:-/anime}"
echo "  FFMPEG_PRE           ${FFMPEG_PRE:-<empty>}"
echo "  FFMPEG_EXTRA         ${FFMPEG_EXTRA:-<empty>}"
echo

args=(
  --movies /movies
  --tv     /tv
  --anime  "${ANIME_PATH:-/anime}"
  --length      "${LENGTH:-5}"
  --resolution  "${RESOLUTION:-720}"
  --crf         "${CRF:-28}"
  --timeout     "${TIMEOUT:-30}"
  --interval    "${INTERVAL:-21600}"
)

[[ "${FORCE:-}"    == "true" ]] && args+=( --force )
[[ "${DAEMON:-}"   == "true" ]] && args+=( --daemon )
[[ "${NO_AUDIO:-}" == "true" ]] && args+=( --no-audio )

[[ -n "${FFMPEG_PRE:-}"   ]] && args+=( --ffmpeg-pre="${FFMPEG_PRE}" )
[[ -n "${FFMPEG_EXTRA:-}" ]] && args+=( --ffmpeg-extra="${FFMPEG_EXTRA}" )

exec python /app/media_theme_processor.py "${args[@]}"
