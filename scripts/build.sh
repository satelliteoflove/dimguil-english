#!/bin/sh
# Build a patched Rev 1 disc image natively on Linux.
#
# Expects rips/clean/dimguil (+ rips/clean/dimguil.xml, with forced LBAs) from:
#   dumpsxiso -l -x rips/clean/dimguil -s rips/clean/dimguil.xml "<Rev 1>.cue"
# Needs: JRE 21+, armips and mkpsxiso on PATH (or ARMIPS / MKPSXISO set).
#
# Steps:
#   1. dump the JP script from the clean files into rips/stage/out/dumps
#   2. restore the redacted JP `source` fields into staged copies of translations/*.json
#      (committed files stay redacted; the encoder falls back to `source` for untranslated strings)
#   3. import the edited font sheet into DATA00/SYSCG.BIN
#   4. encode text + binary patches into rips/dirty/dimguil
#   5. assemble vwf.asm (armips) into the executable and overlays
#   6. relocate files that outgrew their sectors (scripts/relocate.py)
#   7. overlay rips/dirty onto rips/clean and rebuild with mkpsxiso -> rips/iso/dimguil-en.cue
set -eu
cd "$(dirname "$0")/.."
ROOT=$(pwd)
ARMIPS=${ARMIPS:-armips}
MKPSXISO=${MKPSXISO:-mkpsxiso}
JAR=build/libs/dimguil-patcher-1.0-SNAPSHOT.jar

[ -d rips/clean/dimguil ] || { echo "missing rips/clean/dimguil (see header)"; exit 1; }
[ -f "$JAR" ] || ./gradlew -q jar

# fresh staging + dirty trees
rm -rf "$ROOT/rips/stage" "$ROOT/rips/dirty" "$ROOT/rips/iso"
mkdir -p rips/stage/translations rips/dirty/dimguil/DATA00 rips/iso
ln -s ../../tables rips/stage/tables
ln -s ../../sections.json rips/stage/sections.json
ln -s ../../binary rips/stage/binary
ln -s .. rips/stage/rips

echo "== dump + merge"
(cd rips/stage && java -jar "$ROOT/$JAR" dump > /dev/null)
for t in translations/*.json; do
  f=$(basename "$t")
  python3 scripts/merge_source.py "rips/stage/out/dumps/$f" "$t" "rips/stage/translations/$f"
done

echo "== font"
python3 scripts/tim.py import rips/clean/dimguil/DATA00/SYSCG.BIN 0x400 SYSCG_000001_04b_01c.png \
  rips/dirty/dimguil/DATA00/SYSCG.BIN

echo "== encode"
(cd rips/stage && java -jar "$ROOT/$JAR" encode-all 2>&1 | grep -E "exceeded|ERROR" || true)

echo "== asm"
(cd rips && "$ARMIPS" ../vwf.asm && for a in ../asm/*.asm; do "$ARMIPS" "$a"; done)

echo "== relocate"
python3 scripts/relocate.py rips/clean/dimguil.xml rips/dirty/dimguil rips/iso/disc.xml

echo "== disc"
cp -al rips/clean/dimguil rips/iso/dimguil
(cd rips/dirty/dimguil && find . -type f) | while read -r f; do
  rm -f "rips/iso/dimguil/$f"; cp "rips/dirty/dimguil/$f" "rips/iso/dimguil/$f"; echo "  $f"
done
(cd rips/iso && "$MKPSXISO" -q -y -o dimguil-en.bin -c dimguil-en.cue disc.xml)
echo "built rips/iso/dimguil-en.cue"
