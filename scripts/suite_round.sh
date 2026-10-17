#!/bin/sh
# Install a built disc as the suite's disc under test and run a full suite round on it.
#
#   scripts/suite_round.sh BUILD_DIR LABEL "NOTE" [regress.py options...]
#
# BUILD_DIR is a build's rips/iso (dimguil-en.bin, dimguil-en.cue and the dimguil/ file
# tree). LABEL names the build in BUILD.txt and in the archive folder later, usually the
# commit (e3d5cd3). The harness code that runs is this checkout's scripts/harness/, so run
# it from the copy whose harness you mean to test: the main copy for committed code, or a
# worktree (scripts/worktree.sh) at a chosen commit. Meant to be started in the
# background; the round's line in rips/harness/regress/rounds.jsonl is the result.
set -eu
cd "$(dirname "$0")/.."
BUILD=$1; LABEL=$2; NOTE=$3; shift 3
D=rips/harness/disc
[ -e rips/harness/regress/LOCK ] && { echo "a round is running: $(cat rips/harness/regress/LOCK)" >&2; exit 1; }
for f in dimguil-en.bin dimguil-en.cue dimguil/SLPS_026.91 dimguil/BATTLE.BIN; do
  [ -f "$BUILD/$f" ] || { echo "missing $BUILD/$f" >&2; exit 1; }
done
MD5=$(md5sum "$BUILD/dimguil-en.bin" | cut -d' ' -f1)
OLD=$(md5sum "$D/dimguil-en.bin" | cut -d' ' -f1)
if [ "$MD5" != "$OLD" ]; then
  # archive the current disc under its label (the word after "build " in BUILD.txt)
  PREV=$(sed -n 's/^build \([^ ]*\).*/\1/p' "$D/BUILD.txt" | head -1)
  [ -n "$PREV" ] || PREV=unlabeled-$(date +%s)
  if [ ! -e "$D/$PREV" ]; then
    mkdir -p "$D/$PREV/dimguil"
    cp "$D/dimguil-en.bin" "$D/dimguil-en.cue" "$D/BUILD.txt" "$D/$PREV/"
    cp -r "$D"/dimguil/. "$D/$PREV/dimguil/"
  fi
  cp "$BUILD/dimguil-en.bin" "$D/dimguil-en.bin.tmp" && mv "$D/dimguil-en.bin.tmp" "$D/dimguil-en.bin"
  cp "$BUILD/dimguil-en.cue" "$D/dimguil-en.cue"
  for f in SLPS_026.91 BATTLE.BIN CMAIN.BIN CMENU.BIN HAZURE.BIN JOUKA.BIN MAZE.BIN MCARD.BIN; do
    cp "$BUILD/dimguil/$f" "$D/dimguil/$f"
  done
  echo "build $LABEL, md5 $MD5, from $BUILD, installed $(date -Iseconds)" > "$D/BUILD.txt"
fi
# t5bad's event box cases write strings at their offsets in the disc's own EVENTMES
mkdir -p "$D/dimguil/DATA06" && cp "$BUILD/dimguil/DATA06/EVENTMES.BIN" "$D/dimguil/DATA06/EVENTMES.BIN"
[ "$(md5sum "$D/dimguil-en.bin" | cut -d' ' -f1)" = "$MD5" ] || { echo "install mismatch" >&2; exit 1; }
echo "disc $LABEL md5 $MD5 installed; starting round"
exec python3 -u scripts/harness/regress.py --note "$NOTE" "$@"
