; Translation: the tavern joke names, Alstron's 'A' (NPC_MES1 60).
;
; Several greetings react to a party character with a joke name. Alstron's 1:60 ("I once
; saw a grave bearing that very name") and his gift of 100 G go to a member named あ, the
; first letter of the hiragana grid; the English line says 'A'. Guy's party's picker
; (MCARD 0x800bdc08) tests it in three places as three bytes: name[0] == 0x40 (あ),
; name[1] == 0xff (the terminator) and name[2] == name[0] (0x40, the byte after the
; terminator, which happens to equal あ). A name typed on the patch's Latin grid is
; stored one code per letter (A = 0x0b), then 0xff and 0x40, so 'A' is 0b ff 40: each
; site now tests name[0] against 0x0b and name[2] against 0x40, loaded in the free load
; delay slot. a1 held name[0] for that test only; it's written again before any other read.
;
; The other joke names can't be switched this way (docs/re/bugs.md 2.9): Lychee's
; 'Mule' (1:68, 8 bytes at 0x800a1ea8) and Lilia's 'Richguy' (1:75 and 3:48, 6 bytes) and
; Alba's 'Appraiser' (2:50, 6 bytes) are compared with the list's bytes loaded signed, so
; the terminator never matches; 'Richguy' needs 9 bytes, and 'Appraiser' is longer than
; a name can be. Chris approved localizing the checks (2026-10-19).
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800bdd2c                 ; the party flag loop
    addiu   v0, zero, 0x0b      ; was 0x40 (あ)
.org 0x800bdd4c                 ; was nop (load delay of lbu v0, 2(a0))
    addiu   a1, zero, 0x40      ; bne v0, a1 now tests the byte after the terminator
.org 0x800be27c                 ; the 100 G gift, first path
    addiu   t0, zero, 0x0b      ; was 0x40
.org 0x800be2ec
    addiu   a1, zero, 0x40      ; was nop
.org 0x800be60c                 ; the 100 G gift, second path
    addiu   t0, zero, 0x0b      ; was 0x40
.org 0x800be67c
    addiu   a1, zero, 0x40      ; was nop

.close
