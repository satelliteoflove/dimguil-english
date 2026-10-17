#!/bin/sh
# Make a separate working copy for one agent or one job, so builds and edits don't
# collide (docs/agent-workflow.md).
#
#   scripts/worktree.sh NAME [START]     new branch wt/NAME from START (default main)
#   scripts/worktree.sh NAME --existing BRANCH
#
# The copy goes in ../worktrees/NAME (beside the repo). Its rips/ is its own, so its
# builds land in its own rips/iso, rips/dirty and rips/stage. Shared, read-mostly data is
# linked from the main copy:
#   rips/clean     the extracted original disc (never written)
#   rips/harness   the suite's cases, states and rounds (only the suite runner writes
#                  rips/harness/regress; see agent-workflow.md)
#   rips/states    the standard test states (mkstates.py)
#   rips/probe     probe helpers the suite's screen cases import (fixstate.py)
# Remove with: git worktree remove ../worktrees/NAME (then delete the branch if merged).
set -eu
cd "$(dirname "$0")/.."
MAIN=$(pwd)
NAME=$1; shift
DEST="$MAIN/../worktrees/$NAME"
[ -e "$DEST" ] && { echo "exists: $DEST"; exit 1; }
if [ "${1:-}" = "--existing" ]; then
  git worktree add -q "$DEST" "$2"
else
  git worktree add -q -b "wt/$NAME" "$DEST" "${1:-main}"
fi
mkdir -p "$DEST/rips"
for d in clean harness states probe; do
  [ -e "$MAIN/rips/$d" ] && ln -s "$MAIN/rips/$d" "$DEST/rips/$d"
done
[ -f "$MAIN/rips/testsave.mcd" ] && cp "$MAIN/rips/testsave.mcd" "$DEST/rips/"
echo "$DEST"
