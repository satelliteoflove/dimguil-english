#!/bin/sh
# Copy a tested build next to the Rev 1 image as Chris's playtest image.
#
#   scripts/publish_test.sh [BUILD_DIR] [--text-only]
#
# BUILD_DIR holds dimguil-en.bin and dimguil-en.cue (default rips/iso). The disc is
# named by its bin md5, and it's published only if a valid round in
# rips/harness/regress/rounds.jsonl passed every case on that md5 (the rule in
# docs/agent-workflow.md: a build is published only after a full suite round on that
# exact disc). --text-only skips that check, for a build whose only change is text
# that the fit checkers cover; say so when reporting.
set -e
cd "$(dirname "$0")/.."
MAIN=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)
BUILD=rips/iso
SKIP=
for a in "$@"; do
  case "$a" in
    --text-only) SKIP=1 ;;
    *) BUILD=$a ;;
  esac
done
BIN="$BUILD/dimguil-en.bin"
[ -f "$BIN" ] || { echo "no $BIN" >&2; exit 1; }
MD5=$(md5sum "$BIN" | cut -d' ' -f1)
if [ -z "$SKIP" ]; then
  python3 - "$MAIN/rips/harness/regress/rounds.jsonl" "$MD5" <<'EOF' || { echo "refused: no passing round on md5 $MD5" >&2; exit 1; }
import json, sys
path, md5 = sys.argv[1], sys.argv[2]
for line in open(path):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if (r.get('disc_md5') == md5 and r.get('valid') and not r.get('aborted')
            and not r.get('partial')
            and r.get('cases') and r.get('passed') == r.get('cases')):
        print(f"round {r['date']}: {r['passed']} of {r['cases']} on {md5}")
        sys.exit(0)
sys.exit(1)
EOF
fi
DEST="$MAIN/../Wizardry - Dimguil (English WIP)"
# Copy, then rename into place: a game already running from the old image (say, over an
# sshfs mount) keeps reading the old file until it's restarted.
cp "$BIN" "$DEST.bin.tmp" && mv "$DEST.bin.tmp" "$DEST.bin"
sed 's|^FILE "dimguil-en.bin"|FILE "Wizardry - Dimguil (English WIP).bin"|' "$BUILD/dimguil-en.cue" > "$DEST.cue.tmp" && mv "$DEST.cue.tmp" "$DEST.cue"
echo "$(git rev-parse --short HEAD) md5 $MD5 $(date -Iseconds)" > "$DEST.version.txt"
[ "$(md5sum "$DEST.bin" | cut -d' ' -f1)" = "$MD5" ] || { echo "copy mismatch" >&2; exit 1; }
echo "published $DEST.cue ($(cat "$DEST.version.txt"))"
if [ -f "$MAIN/rips/testsave.mcd" ]; then
    cp "$MAIN/rips/testsave.mcd" "$DEST test save.mcd.tmp" && mv "$DEST test save.mcd.tmp" "$DEST test save.mcd"
    echo "published $DEST test save.mcd"
fi
