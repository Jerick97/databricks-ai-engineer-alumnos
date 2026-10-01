#!/bin/zsh
set -euo pipefail
VIDEO_ROOT="${0:A:h}"
export npm_config_cache="${TMPDIR:-/tmp}/sbs-video-npm"
for VIDEO_NAME in 01-ingesta-publicacion 02-consulta-aplicacion; do
  cd "$VIDEO_ROOT/$VIDEO_NAME"
  npx --yes hyperframes@0.8.98 check --snapshots
  npx --yes hyperframes@0.8.98 render --quality delivery --fps 30 --workers 1 --output "$VIDEO_ROOT/$VIDEO_NAME.mp4"
  ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,codec_type,width,height -of json "$VIDEO_ROOT/$VIDEO_NAME.mp4" > "$VIDEO_ROOT/$VIDEO_NAME/render-probe.json"
done
