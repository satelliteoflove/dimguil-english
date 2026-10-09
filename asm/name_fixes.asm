; Misspelled built-in English names: BATTLE.BIN's copy.
;
; BATTLE.BIN carries a monster record of its own (the 0xd0-byte layout of DATA02's
; M_DTnnn.BIN, six 18-byte name slots ending in {ff40}). Its Dragonare is fixed here, as
; scripts/namefixes.py fixes the DATA02 records; vwf.asm copies BATTLE.BIN into dirty/
; after the binary patches are applied, so the copy has to be patched in asm. Glyph
; codes are the single-letter ones from tables/dimguil_enc.tbl.
.psx

.open "dirty/dimguil/BATTLE.BIN", 0x800a1000
.org 0x800d749c
.area 0x12
    ; Dragonaire (was Dragonare)
    .db 0x0e, 0x36, 0x25, 0x2b, 0x33, 0x32, 0x25, 0x2d, 0x36, 0x29, 0xff, 0x40
    .fill 6, 0
.endarea
.org 0x800d74c0
.area 0x12
    ; Dragonaires (was Dragonares)
    .db 0x0e, 0x36, 0x25, 0x2b, 0x33, 0x32, 0x25, 0x2d, 0x36, 0x29, 0x37, 0xff, 0x40
    .fill 5, 0
.endarea
.close
