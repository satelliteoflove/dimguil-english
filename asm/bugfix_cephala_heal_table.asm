; Game bug fix: Cephala's healing lines and cures line up again (NPC_MES3 132-144).
;
; Fontana's handler picks Cephala's script blocks by number, and the numbers assume a
; block for 3:134 ("I don't think I can treat that person.") that the array lacks: 9 is
; the offer (3:132), 10 "nothing wrong" (3:133), and 3:135 is already block 11. So every
; choice from 11 up ran the next block: Dial for "out of magic", Dialko for the dead,
; Latumofis for paralysis, Kadorto at the wrong stage, and so on. The cancel (20, 3:144)
; was numbered against the real array and is right.
;
; Each number goes down by one, except stage 1's stone/dead "can't treat", which goes
; to block 14 (3:138): the same line as the missing 3:134, word for word in Japanese.
; Real array: 11 Dialko, 12 Latumofis, 13 Madi, 14 can't treat, 15 Kadorto, 16 no magic,
; 17 Dial, 18 Dialma, 19 Madi. docs/re/bugs.md 1.3.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800d1934
    addiu   v1, zero, 0x10      ; 20% out of magic (was 0x11)
.org 0x800d1994
    addiu   v1, zero, 0xe       ; stage 1, stone or dead: can't treat (was 0xb)
.org 0x800d19ac
    addiu   v1, zero, 0xb       ; stage 1, paralysis: Dialko (was 0xc)
.org 0x800d19c8
    addiu   v1, zero, 0xc       ; stage 1, poison: Latumofis (was 0xd)
.org 0x800d1a28
    addiu   v1, zero, 0xd       ; stages 2-3, poison/paralysis/stone: Madi (was 0xe)
.org 0x800d1a88
    addiu   v1, zero, 0xe       ; stage 2, dead or ashes: can't treat (was 0xf)
.org 0x800d1ae8
    addiu   v1, zero, 0xf       ; stage 3, dead or ashes: Kadorto (was 0x10)
.org 0x800d1b4c
    addiu   v1, zero, 0x11      ; stage 1, hurt: Dial (was 0x12)
.org 0x800d1bb0
    addiu   v1, zero, 0x12      ; stage 2, hurt: Dialma (was 0x13)
.org 0x800d1c10
    addiu   v1, zero, 0x13      ; stage 3, hurt: Madi (was 0x14)
.close
