; Game bug fix (balance-changing): the Ninja's and Monk's class hit effects now apply.
;
; battle_derive_stats (0x800a1830) rebuilds a character's battle block in the work copy
; new_char (0x8008ff10, held in s0 from 0x800a18bc) and gives two classes a hit effect of
; their own before the gear's: a Ninja (class 12) beheading (+0x8c = 0x40) at 11% (+0x93),
; a Monk (13) knock-out (0x20) at 11% (+0x92). The test at 0x800a197c read the class from
; s3, which this function never loads: it holds the caller's value, 2 at battle start or a
; panel row's Y on a redraw, never 12 or 13 (docs/re/ninja.md; emulator: 2,700 calls, s3
; only 2, 0xc0, 0xda). So neither bonus ever applied in the original game.
;
; Now it reads the class from the work copy the way the same function does at 0x800a1a1c
; (class_sex +0x0b & 0x7f, which drops the female bit). The lui/addiu that built the
; new_char address in a0 become a move from s0, which holds the same address; v0 is
; reloaded with 12 at 0x800a1980 as before.
;
; Effect: a bare-handed Ninja's beheading goes from 20% to 31% a hand (the bare-hand 20 at
; 0x800a2880 adds to it), an armed Ninja's from the gear's chances to 11% more, and the
; same for a Monk's knock-out. Chris approved the fix on 2026-10-17 as a disclosed balance
; change (docs/re/bugs.md 3.5, decisions.md).
.psx
.open "dirty/dimguil/BATTLE.BIN", 0x800a1000

.org 0x800a1974                 ; was lui v0, 0x8009 / addiu a0, v0, -0xf0 / andi v1, s3, 0xff
.area 12
    lbu     v1, 0x0b(s0)        ; class_sex of new_char
    move    a0, s0              ; new_char (load delay)
    andi    v1, v1, 0x7f        ; the class
.endarea

.close
