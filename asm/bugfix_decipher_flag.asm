; Game bug fix: a full Decipher table no longer skips Cresson's speech (NPC_MES4 24-29).
;
; marks[0] bit 1 (roster +0xca) meant two things. Cresson's decipher check set it on
; every member at a 100% match (talk_cresson), and handler 22, Cresson on Cleo and
; Bergamot after the control room, reads it as "already heard this" and sets it once the
; speech has played. Nothing else reads the bit, so the decipher check's flag only ever
; hid the speech from a party that had finished the table. It no longer sets it.
; docs/re/bugs.md 1.7.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800d77e0
    ori     v1, v1, 0           ; was: ori v1, v1, 2
.close
