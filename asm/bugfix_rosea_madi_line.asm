; Game bug fix: Rosea's Madi heal plays her Madi line (NPC_MES2 134).
;
; Rosea's healing blocks in Balbo's handler are static script data: 20 Dial (2:132),
; 21 Dialma (2:133), 22 Madi, 23 cancel (2:135, "I see... Do take care."). Block 22 was
; block 23's face and line with the Madi cure added, so a Madi heal said "take care".
; 2:134 ("Oh my, how awful!" / Madi / "There, all better.") was never used.
; Block 22 is face(6, 4, 109) say(135) cure(5) end; this makes it face(6, 0, 109)
; say(134), as blocks 20 and 21 are. docs/re/bugs.md 1.2.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800a4df0
    .dh 0                       ; expression, was 4 (as block 23)
.org 0x800a4df6
    .dh 134                     ; was 135
.close
