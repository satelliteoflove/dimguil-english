; Temple of Cant (JOUKA.BIN): space out the resurrection chant. The four words are
; drawn one at a time at fixed x positions sized for 2-4 kana; "Murmur-" ran into
; "Chant-". Original x: 0x4c, 0x70, 0xac, 0xd0 (y 0xa6).
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800ca9b8
    addiu   a0, zero, 0x40      ; Murmur-  (branch delay slot; constant only)
.org 0x800caa08
    addiu   a0, zero, 0x76      ; Chant-
.org 0x800caa30
    addiu   a0, zero, 0xa6      ; Pray-
.org 0x800caa5c
    addiu   a0, zero, 0xcc      ; Invoke
.close
