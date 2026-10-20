; Reopened content: Reiran's young-Ninja greeting (NPC_MES2 64, NPC_MES3 66), "Is that a
; Thieves Dagger? {name}, a Ninja at your age? How marvelous."
;
; Reiran's greeting picker tests each member for a Ninja under 20 (age 10-19; new
; characters start at 15-20, so 15-19 in play) and, when one is found, copies that
; member's name into the line. Two bugs, the first hiding the second:
;
; 1. Both class tests read class_sex (+0x0b) and keep bit 7, the female bit, with
;    andi 0x80, then compare the result with 0xc, the Ninja class. 0 or 0x80 never equals
;    0xc, so the line could never show. The class is bits 0-6: andi 0x7f, as the other
;    class tests in the game do (training_create, Guy's party's Thief loop).
; 2. The name copy is only on one of the picker's two paths. With story_flags bit 28 set
;    (only the card game's code sets it), the line is a 50% pick and copies the Ninja's
;    name into 0x80089ac0 for {ff12}. With bit 28 clear, the usual case, the line is
;    picked every time and the name isn't copied, so {ff12} showed whatever name the
;    buffer last held: the last party member (the status panel draws names through it)
;    or, at Fontana's, the first. That path now jumps to the other path's code, which
;    sets the same line and expression and copies the name.
;
; Two copies of the picker: Balbo's party (0x800cda60, for NPC_MES2) and Fontana's
; (0x800d3664, for NPC_MES3, after the parties reshuffle). Chris approved both fixes
; (2026-10-19). docs/engine-notes.md, "Class tests that mask the wrong bits";
; docs/re/bugs.md 1.17.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800cdb14                 ; Balbo's party: the young-Ninja flag
    andi    v0, v0, 0x7f        ; was: andi v0, v0, 0x80
.org 0x800cde74                 ; Balbo's party: the name copy
    andi    v0, v0, 0x7f
.org 0x800cdf74                 ; Balbo's party, bit 28 clear: was sb v0 / lui v1, then
    j       0x800cddf0          ;   j 0x800cdfb0 setting talk_str_a 0x40, no name copy
    move    a0, zero            ; the copy loop's member index

.org 0x800d3718                 ; Fontana's party: the young-Ninja flag
    andi    v0, v0, 0x7f
.org 0x800d3a78                 ; Fontana's party: the name copy
    andi    v0, v0, 0x7f
.org 0x800d3b78                 ; Fontana's party, bit 28 clear (talk_str_a 0x42)
    j       0x800d39f4
    move    a0, zero

.close
