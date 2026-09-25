#!/bin/sh
# Swap the playtest memory card (scripts/mktestsave.py) into DuckStation's slot 1 for
# Dimguil, keeping your own card; --restore puts yours back. Close the game in
# DuckStation first, or it may write its copy of the old card over the swap.
#
# DuckStation names per-game cards by title, so the English build and the Japanese disc
# share one card: memcards/Wizardry - Dimguil (Japan)_1.mcd.
set -e
cd "$(dirname "$0")/.."
CARD="$HOME/.local/share/duckstation/memcards/Wizardry - Dimguil (Japan)_1.mcd"
MINE="$CARD.mine"
if [ "$1" = "--restore" ]; then
    [ -f "$MINE" ] || { echo "no saved card to restore ($MINE)"; exit 1; }
    mv "$MINE" "$CARD"
    echo "restored your card"
    exit 0
fi
[ -f rips/testsave.mcd ] || { echo "run scripts/mktestsave.py first"; exit 1; }
if [ -f "$CARD" ] && [ ! -f "$MINE" ]; then
    cp "$CARD" "$MINE"
    echo "saved your card as $MINE"
fi
cp rips/testsave.mcd "$CARD"
echo "test card is in slot 1; scripts/use_testsave.sh --restore to switch back"
