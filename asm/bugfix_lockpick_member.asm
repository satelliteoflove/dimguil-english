; Game bug fix: picking a lock uses the chosen character's skill.
;
; Investigate on a locked door asks "Who will pick the lock?". The routine turns the party
; position picked (0x800ae324) into a roster number, stores it at 0x800798d1 (0x800ae39c)
; and checks that character's status from it. The roll then computes the skill, (level,
; + 5 for a Thief or Ninja, + 2 for a Ranger or Bard) x 5 + Luck over 10, against the
; door's difficulty, but takes the roster number for both reads (level and class at
; 0x800aea44, Luck at 0x800aeaac) from 0x80079791 instead: the member picker's blink
; counter (FUN_800ac6bc), which steps 1-5 and back every 4 frames. So the skill was that
; of roster entry 1 to 5, whichever the blink was on, in the party or not; an empty
; entry gave skill 0. Seen in play: the chosen Thief's record was never the one read,
; over 91 logged tries (docs/re/lock-test.md).
;
; Both reads now take 0x800798d1. One instruction each; the base each needs (0x80080000)
; is already in the register, set by the instruction before. Chris decided on 2026-10-13
; to fix it (docs/re/bugs.md 1.14, docs/re/decisions.md 28).
.psx
.open "dirty/dimguil/MAZE.BIN", 0x800a1000

.org 0x800aea44
    lbu     v1, -0x672f(a0)     ; was: lbu v1, 1(s1) (s1 = 0x80079790: the blink counter)

.org 0x800aeaac
    lbu     v1, -0x672f(v0)     ; was: lbu v1, -0x686f(v0) (0x80079791)

.close
