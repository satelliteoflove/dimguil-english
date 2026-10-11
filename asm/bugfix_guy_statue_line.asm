; Game bug fix: Guy's statue warning shows a stranger the right line (NPC_MES1 87).
;
; Handler 7 (talk_scene_guy_statue_a, 0x800c064c) plays Guy's warning about the statue
; on the altar: 1:88 if someone in the party has met Guy, else the stranger's copy. The
; stranger's string was 1:89, "The room up ahead's got some crazy trap in it!", the trap
; warning from handler 10. 1:87 is the "Man with a greatsword" copy of the statue speech
; and was never used; handler 8 pairs 1:86 with 1:295 the same way. docs/re/bugs.md 1.1.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800c0814
    addiu   a1, zero, 0x57      ; was 0x59 (1:89)
.close
