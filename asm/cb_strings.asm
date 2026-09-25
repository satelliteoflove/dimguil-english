; Card game strings kept in the overlays as Shift-JIS and converted to font codes at
; run time. The converter's single-byte table puts ASCII at the same codes as
; Remisse's font (digits, '-', A-Z, a-z, then punctuation), so plain ASCII works; it
; has no digraphs, so each letter is one byte. Every string keeps its original area.
; Runs after catalog_vwf.asm, which creates the dirty copies.

.psx

.open "dirty/dimguil/CMENU.BIN", 0x800a1000
; Shown on the way out of the card game. The caption is drawn at a fixed x that
; centered the Japanese; the leading spaces (4px each) do the same for this.
.org 0x800a1000
.area 0x19
    .asciiz "            Loading..."
.endarea
; Unit card records (0x32 bytes each: Japanese name, English name, stats). The card
; game shows the English field, e.g. when a password is accepted; these match the
; spellings used in MESSAGE.DAT and the Monster Compendium.
.org 0x800a1d32
.area 0x10
    .asciiz "Murphy's Ghost"
.endarea
.org 0x800a1e2c
.area 0x10
    .asciiz "Demon Imp"
.endarea
.org 0x800a1f26
.area 0x10
    .asciiz "Greater Demon"
.endarea
.org 0x800a20b6
.area 0x10
    .asciiz "Were Jaguar"
.endarea
.org 0x800a214c
.area 0x10
    .asciiz "Dullahan"
.endarea
.org 0x800a217e
.area 0x10
    .asciiz "Dragonaire"
.endarea
.org 0x800a2278
.area 0x10
    .asciiz "Ixquic"
.endarea
.close

.open "dirty/dimguil/CMAIN.BIN", 0x800a1000
; Unit card records (0x32 bytes each: Japanese name, English name, stats). The card
; game shows the English field, e.g. when a password is accepted; these match the
; spellings used in MESSAGE.DAT and the Monster Compendium.
.org 0x800a1a7e
.area 0x10
    .asciiz "Murphy's Ghost"
.endarea
.org 0x800a1b78
.area 0x10
    .asciiz "Demon Imp"
.endarea
.org 0x800a1c72
.area 0x10
    .asciiz "Greater Demon"
.endarea
.org 0x800a1e02
.area 0x10
    .asciiz "Were Jaguar"
.endarea
.org 0x800a1e98
.area 0x10
    .asciiz "Dullahan"
.endarea
.org 0x800a1eca
.area 0x10
    .asciiz "Dragonaire"
.endarea
.org 0x800a1fc4
.area 0x10
    .asciiz "Ixquic"
.endarea
; Battle commands and their prompts
.org 0x800a1724
.area 0x0b
    .asciiz "Target"
.endarea
.org 0x800a172f
.area 0x0b
    .asciiz "Master"
.endarea
.org 0x800a173a
.area 0x0e
    .asciiz "Wait"
.endarea
.org 0x800a1748
.area 0x28
    .asciiz "Choose the unit's target."
.endarea
.org 0x800a1770
.area 0x1c
    .asciiz "Choose a Master Card."
.endarea
.close
