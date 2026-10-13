; Temple of Cant (JOUKA.BIN): space out the resurrection chant. The four words are
; drawn one at a time at fixed x positions sized for 2-4 kana; "Murmur-" ran into
; "Chant-". Original x: 0x4c, 0x70, 0xac, 0xd0 (y 0xa6).
;
; The positions put the finished line where the row centers a line (text_at's centering
; starts a line of W px at 168 - (W + 12) / 2: "Not enough gold." at 121), with one
; space (4 px) between the words: widths 45, 35, 28 and 36 px, 156 with the gaps, so
; the line starts at 84. They were 0x40, 0x76, 0xa6, 0xcc, which left the line 10 px
; left of center with 10-14 px gaps (2026-10-13). Rewording a word means redoing these.
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800ca9b8
    addiu   a0, zero, 84        ; Murmur-  (84 + 45 + 4 = 133)  (branch delay slot; constant only)
.org 0x800caa08
    addiu   a0, zero, 133       ; Chant-   (133 + 35 + 4 = 172)
.org 0x800caa30
    addiu   a0, zero, 172       ; Pray-    (172 + 28 + 4 = 204)
.org 0x800caa5c
    addiu   a0, zero, 204       ; Invoke!  (to 240)
.close
