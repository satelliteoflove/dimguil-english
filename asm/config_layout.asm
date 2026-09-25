; Configuration screen (HAZURE.BIN): widen the Sound Mode row so "Stereo" (drawn
; bold when selected) doesn't run into the separator and "Mono".
; Original x: "(" 0xa4, Stereo 0xb0, "/" 0xd0, Mono 0xdc, ")" 0xfc.
.psx
.open "dirty/dimguil/HAZURE.BIN", 0x800a1000
.org 0x800ac320
    addiu   a0, zero, 0xe2      ; "/"   (was 0xd0)
.org 0x800ac34c
    addiu   a0, zero, 0xec      ; Mono  (was 0xdc)
.org 0x800ac378
    addiu   a0, zero, 0x112     ; ")"   (was 0xfc)
.close
