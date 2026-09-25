#!/bin/sh
# Copy the current build next to the Rev 1 image as a playtest image.
set -e
cd "$(dirname "$0")/.."
DEST="../Wizardry - Dimguil (English WIP)"
cp rips/iso/dimguil-en.bin "$DEST.bin"
sed 's|^FILE "dimguil-en.bin"|FILE "Wizardry - Dimguil (English WIP).bin"|' rips/iso/dimguil-en.cue > "$DEST.cue"
echo "$(git rev-parse --short HEAD) $(date -Iseconds)" > "$DEST.version.txt"
echo "published $DEST.cue ($(cat "$DEST.version.txt"))"
