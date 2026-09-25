#!/bin/sh
# Copy the current build next to the Rev 1 image as a playtest image.
set -e
cd "$(dirname "$0")/.."
DEST="../Wizardry - Dimguil (English WIP)"
# Copy, then rename into place: a game already running from the old image (say, over an
# sshfs mount) keeps reading the old file until it's restarted.
cp rips/iso/dimguil-en.bin "$DEST.bin.tmp" && mv "$DEST.bin.tmp" "$DEST.bin"
sed 's|^FILE "dimguil-en.bin"|FILE "Wizardry - Dimguil (English WIP).bin"|' rips/iso/dimguil-en.cue > "$DEST.cue.tmp" && mv "$DEST.cue.tmp" "$DEST.cue"
echo "$(git rev-parse --short HEAD) $(date -Iseconds)" > "$DEST.version.txt"
echo "published $DEST.cue ($(cat "$DEST.version.txt"))"
if [ -f rips/testsave.mcd ]; then
    cp rips/testsave.mcd "$DEST test save.mcd.tmp" && mv "$DEST test save.mcd.tmp" "$DEST test save.mcd"
    echo "published $DEST test save.mcd"
fi
