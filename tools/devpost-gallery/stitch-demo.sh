#!/usr/bin/env bash
# Stitch: open + trimmed human demo + Codex + end → privilege-pdf-lifecycle.mp4
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLIPS="$ROOT/docs/media/clips"
SLIDES="$CLIPS/slides"
MEDIA="$ROOT/docs/media"
DRAFT="$CLIPS/demo-video-vDRAFT.mov"
TMP="$CLIPS/.stitch-tmp"
W=1920
H=1248
# Drop last ~2.5s of stop-recording UI
BODY_DUR=124.0
OPEN_DUR=9
CODEX_DUR=8
END_DUR=7

export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"
cd "$ROOT/tools/devpost-gallery"
node capture-slides.mjs

rm -rf "$TMP"
mkdir -p "$TMP"

# Body: trim + scale to slide canvas (keep aspect, pad if needed)
ffmpeg -y -i "$DRAFT" -t "$BODY_DUR" \
  -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30" \
  -c:v libx264 -pix_fmt yuv420p -an "$TMP/body.mp4"

still() {
  local img="$1" dur="$2" out="$3"
  ffmpeg -y -loop 1 -i "$img" -t "$dur" \
    -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30" \
    -c:v libx264 -pix_fmt yuv420p -an "$out"
}

still "$SLIDES/open.png" "$OPEN_DUR" "$TMP/open.mp4"
still "$SLIDES/codex.png" "$CODEX_DUR" "$TMP/codex.mp4"
still "$SLIDES/end.png" "$END_DUR" "$TMP/end.mp4"

printf "file '%s'\nfile '%s'\nfile '%s'\nfile '%s'\n" \
  "$TMP/open.mp4" "$TMP/body.mp4" "$TMP/codex.mp4" "$TMP/end.mp4" > "$TMP/list.txt"

ffmpeg -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$TMP/joined.mp4"

OUT="$MEDIA/privilege-pdf-lifecycle.mp4"
ffmpeg -y -i "$TMP/joined.mp4" -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$OUT"
cp -f "$OUT" "$CLIPS/demo-video-stitched.mp4"

DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT")
echo "Wrote $OUT (${DUR}s)"
rm -rf "$TMP"
