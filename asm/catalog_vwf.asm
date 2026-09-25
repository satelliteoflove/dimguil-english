; Variable-width text for the glyph-list renderer: Boltac's catalog and the Tavern's
; Monster Compendium (two copies in JOUKA.BIN), and the card game (CMENU.BIN and
; CMAIN.BIN). It turns a string into a list of glyph words once, then draws the list
; every frame. Each word holds the glyph's font-sheet u,v, its texture page
; and a 3-bit width field sized for kana, so with Remisse's font single letters get
; spaced like digraphs ("W ea p on s").
;
; Glyph word layout: bits 0-7 u, 8-15 v, 16-21 texture page (0x0f = the SYSCG font,
; 0x1f = kanji), 24-26 type (6 = normal, 3 = half width), 27-29 width-5 (7 = newline).
; Single-byte code c sits at u = (c % 21) * 12, v = (c / 21) * 12 + 0x50.
;
; cat_adv recovers c from u,v and advances by VWF_LUT[c] + 1 (Remisse's table at
; 0x80060e97, vwf.asm), the same spacing the main text engine uses. Kanji and anything
; outside the table keep 12px. The table ends with the ma me wa we mo mi digraphs at
; 0xd2-0xd7, so the bound is 0xd8; stopping at 0xd1 spaced those a pixel short. The pen advances in the draw loop, one or two centering
; measures, and the per-glyph measure used for struct widths and line wrapping.

.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800
; GsPushMatrix/GsPopMatrix overflow messages and an unreferenced "not implemented"
; string; only ever passed to printf on a matrix stack error.
.org 0x80073c78
.area 0x80073cf4-.
; a0 = glyph word, v1 = pen x. Returns v0 = new pen x. Clobbers t7-t9.
; (Not a1: 0x800e306c passes its a1 through to the draw loop untouched.)
cat_adv:
    srl     t9, a0, 16
    andi    t9, t9, 0x3f
    xori    t9, t9, 0x0f
    bnez    t9, @@fixed         ; not the SYSCG font page
    andi    t8, a0, 0xff        ; u
    srl     t9, a0, 8
    andi    t9, t9, 0xff
    addiu   t9, t9, -0x50       ; v - 0x50
    bltz    t9, @@fixed
    sll     t7, t9, 2
    addu    t7, t7, t9
    sll     t7, t7, 2
    addu    t7, t7, t9          ; (v - 0x50) * 21
    addu    t7, t7, t8          ; + u = c * 12
    ori     t9, zero, 12
    divu    t7, t9
    mflo    t7                  ; c
    sltiu   t9, t7, 0xd8        ; the table runs to 0xd7 (mi)
    beqz    t9, @@fixed
    lui     t9, 0x8006
    addu    t9, t9, t7
    lbu     v0, 0x0e97(t9)
    nop
    addu    v0, v0, v1
    jr      ra
    addiu   v0, v0, 1
@@fixed:
    jr      ra
    addiu   v0, v1, 12
.endarea
.close

; Each advance site first handles half-width glyphs (+6), then has two modes picked by a
; flag byte: mode 0 adds the glyph type (12), mode 8 adds width + 4. Normal glyphs
; (type 12) now go to cat_adv in both modes; other types keep the old rule.
;
; The macros are keyed to one instruction in each copy; the code around it is identical
; in every copy apart from the flag byte's address.

; Centering measure. anchor = "srl v0, v0, 0x1b"; the pen is at 0(xreg), the width in
; wreg, 12 in t3, the type in a2. The glyph word is kept in t5.
.macro ctr_vwf, anchor, xreg, wreg
.org anchor - 0xc
    lw      t5, 0(v0)
.org anchor - 4
    srl     v1, t5, 0x17
    srl     v0, t5, 0x1b
.org anchor + 0x44
    bne     a2, t3, anchor + 0x60
    andi    v0, a0, 8
    lhu     v1, 0(xreg)
    jal     cat_adv
    move    a0, t5
    j       anchor + 0x7c
    nop
    lhu     t6, 0(xreg)                 ; anchor + 0x60: other glyph types
    nop
    beqz    v0, anchor + 0x7c
    addu    v0, t6, a2
    j       anchor + 0x7c
    addu    v0, t6, wreg
    nop
.org anchor + 0x7c                      ; sh v0, 0(xreg)
.endmacro

; Draw loop with the pen at 4(s1). anchor = "srl v1, v1, 0x1b"; type in a1, width in
; v1, 12 in s6. The glyph word is kept in t2.
.macro draw_vwf, anchor
.org anchor - 0xc
    lw      t2, 0(v0)
.org anchor - 4
    srl     v0, t2, 0x17
    srl     v1, t2, 0x1b
.org anchor + 0x44
    bne     a1, s6, anchor + 0x60
    andi    v0, a0, 8
    lhu     v1, 4(s1)
    jal     cat_adv
    move    a0, t2
    j       anchor + 0x8c
    sh      v0, 4(s1)
    lhu     t3, 4(s1)                   ; anchor + 0x60: other glyph types
    nop
    beqz    v0, anchor + 0x74
    addu    v0, t3, a2
    addu    v0, t3, v1
    j       anchor + 0x8c               ; anchor + 0x74
    sh      v0, 4(s1)
.endmacro

; Per-glyph measure, a leaf (a0 = &x, a1 = &word). anchor = "srl v0, v0, 0x1b".
; The mode flags move to t1 so a1 survives; ra is parked in t6 around the call.
.macro msr_vwf, anchor, flagoff
.org anchor + 0x20
    lbu     t1, flagoff(v0)
.org anchor + 0x28
    andi    v0, t1, 2
.org anchor + 0x4c
    bne     a2, t0, anchor + 0x78
    andi    v0, t1, 8
    move    t6, ra
    move    t5, a0
    lw      a0, 0(a1)
    lhu     v1, 0(t5)
    jal     cat_adv
    nop
    move    ra, t6
    j       anchor + 0x8c
    move    a0, t5
    lhu     t4, 0(a0)                   ; anchor + 0x78: other glyph types
    nop
    beqz    v0, anchor + 0x8c
    addu    v0, t4, a2
    addu    v0, t4, a3
.org anchor + 0x8c                      ; sh v0, 0(a0)
.endmacro

; The string builders take a single-byte glyph's width field from a 0xd0-entry table,
; so Remisse's digraphs 0xd2-0xd7 (ma me wa we mo mi) read whatever byte follows it. A
; 7 there is the newline marker and broke "game" into "ga" + a line break. The field
; no longer sets the advance (cat_adv does), and real entries are 0-3.
.macro width_mask, addr                 ; andi v0, v0, 7 before sll v0, v0, 0x1b
.org addr
    andi    v0, v0, 3
.endmacro

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
; Catalog copy. Its draw loop keeps the pen in a global (0x800ec99c, -0x3664(s4)),
; so it's patched by hand: glyph word in t2, type in a1, width in v1, 12 in s6.
.org 0x800e33bc
    lw      t2, 0(v0)
.org 0x800e33c4
    srl     v0, t2, 0x17
    srl     v1, t2, 0x1b
.org 0x800e340c
    bne     a1, s6, @@draw_other
    andi    v0, a0, 8
    lhu     v1, -0x3664(s4)
    jal     cat_adv
    move    a0, t2
    j       0x800e3454
    sh      v0, -0x3664(s4)
@@draw_other:
    lhu     t3, -0x3664(s4)
    nop
    beqz    v0, @@draw_store
    addu    v0, t3, a2
    addu    v0, t3, v1
@@draw_store:
    j       0x800e3454
    sh      v0, -0x3664(s4)
    ctr_vwf     0x800e30dc, a3, t0
    msr_vwf     0x800e4628, -0x3758
    width_mask  0x800e2bdc

; Monster Compendium copy
    ctr_vwf     0x800e9ce0, a3, t0
    ctr_vwf     0x800e9e68, t0, t1
    draw_vwf    0x800ea1b0
    msr_vwf     0x800eb2f4, -0x3318
    width_mask  0x800e97b0
.close

; Card game menus
.open "clean/dimguil/CMENU.BIN", "dirty/dimguil/CMENU.BIN", 0x800a1000
    ctr_vwf     0x800a6630, a3, t0
    ctr_vwf     0x800a67a4, t0, t1
    draw_vwf    0x800a6aec
    msr_vwf     0x800a7b20, 0x4a4
    width_mask  0x800a6134
.close

; Card battles
.open "clean/dimguil/CMAIN.BIN", "dirty/dimguil/CMAIN.BIN", 0x800a1000
    ctr_vwf     0x800a5c48, a3, t0
    ctr_vwf     0x800a5dbc, t0, t1
    draw_vwf    0x800a6104
    msr_vwf     0x800a7138, -0x402c
    width_mask  0x800a574c
.close
