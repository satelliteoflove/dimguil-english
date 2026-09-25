; Variable-width text for JOUKA's glyph-list renderer (Boltac's catalog, and a second
; copy of the same code for the Tavern's Monster Compendium). That renderer turns a string into a list of glyph words once, then draws
; the list every frame. Each word holds the glyph's font-sheet u,v, its texture page
; and a 3-bit width field sized for kana, so with Remisse's font single letters get
; spaced like digraphs ("W ea p on s").
;
; Glyph word layout: bits 0-7 u, 8-15 v, 16-21 texture page (0x0f = the SYSCG font,
; 0x1f = kanji), 24-26 type (6 = normal, 3 = half width), 27-29 width-5 (7 = newline).
; Single-byte code c sits at u = (c % 21) * 12, v = (c / 21) * 12 + 0x50.
;
; cat_adv recovers c from u,v and advances by VWF_LUT[c] + 1 (Remisse's table at
; 0x80060e97, vwf.asm), the same spacing the main text engine uses. Kanji and anything
; outside the table keep 12px. Three places advance the pen: the draw loop, the
; centering measure in 0x800e306c, and the measure used for struct widths and line
; wrapping (0x800e461c).

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
    sltiu   t9, t7, 0xd1
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

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
; Each advance site first handles half-width glyphs (+6), then has two modes picked by
; flag 8 at 0x800ec8a8: mode 0 adds the glyph type (12), mode 8 adds width + 4. Normal
; glyphs (type 12) now go to cat_adv in both modes; other types keep the old rule.

; Draw loop (0x800e31b8): keep the glyph word in t2. a1 = type, v1 = width, s6 = 12.
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
.org 0x800e3454

; Centering measure (0x800e306c): keep the word in t5. a2 = type, t0 = width, t3 = 12.
.org 0x800e30d0
    lw      t5, 0(v0)
.org 0x800e30d8
    srl     v1, t5, 0x17
    srl     v0, t5, 0x1b
.org 0x800e3120
    bne     a2, t3, @@ctr_other
    andi    v0, a0, 8
    lhu     v1, 0(a3)
    jal     cat_adv
    move    a0, t5
    j       0x800e3158
    nop
@@ctr_other:
    lhu     t6, 0(a3)
    nop
    beqz    v0, 0x800e3158
    addu    v0, t6, a2
    j       0x800e3158
    addu    v0, t6, t0
    nop
                                ; 0x800e3158: sh v0, 0(a3)
.org 0x800e3158

; Per-glyph measure (0x800e461c, a leaf: a0 = &x, a1 = &word). Keep the mode flags
; in t1 so a1 survives, then send normal glyphs to cat_adv in either mode.
.org 0x800e4648
    lbu     t1, -0x3758(v0)
.org 0x800e4650
    andi    v0, t1, 2
.org 0x800e4674
    bne     a2, t0, @@msr_other ; type != 12
    andi    v0, t1, 8
    move    t6, ra
    move    t5, a0
    lw      a0, 0(a1)
    lhu     v1, 0(t5)
    jal     cat_adv
    nop
    move    ra, t6
    j       0x800e46b4
    move    a0, t5
@@msr_other:                    ; original behaviour: x + width (mode 8) or x + type
    lhu     t4, 0(a0)
    nop
    beqz    v0, 0x800e46b4
    addu    v0, t4, a2
    addu    v0, t4, a3
.org 0x800e46b4                 ; sh v0, 0(a0) follows

; The Monster Compendium's copy: same code, its flags at 0x800ecce8 (-0x3318).
; Draw loop (0x800e9f7c): pen x lives at 4(s1).
.org 0x800ea1a4
    lw      t2, 0(v0)
.org 0x800ea1ac
    srl     v0, t2, 0x17
    srl     v1, t2, 0x1b
.org 0x800ea1f4
    bne     a1, s6, @@draw2_other
    andi    v0, a0, 8
    lhu     v1, 4(s1)
    jal     cat_adv
    move    a0, t2
    j       0x800ea23c
    sh      v0, 4(s1)
@@draw2_other:
    lhu     t3, 4(s1)
    nop
    beqz    v0, @@draw2_store
    addu    v0, t3, a2
    addu    v0, t3, v1
@@draw2_store:
    j       0x800ea23c
    sh      v0, 4(s1)

; Centering measure (0x800e9c64).
.org 0x800e9cd4
    lw      t5, 0(v0)
.org 0x800e9cdc
    srl     v1, t5, 0x17
    srl     v0, t5, 0x1b
.org 0x800e9d24
    bne     a2, t3, @@ctr2_other
    andi    v0, a0, 8
    lhu     v1, 0(a3)
    jal     cat_adv
    move    a0, t5
    j       0x800e9d5c
    nop
@@ctr2_other:
    lhu     t6, 0(a3)
    nop
    beqz    v0, 0x800e9d5c
    addu    v0, t6, a2
    j       0x800e9d5c
    addu    v0, t6, t0
    nop
.org 0x800e9d5c                 ; sh v0, 0(a3)

; Per-glyph measure (0x800eb2e8).
.org 0x800eb314
    lbu     t1, -0x3318(v0)
.org 0x800eb31c
    andi    v0, t1, 2
.org 0x800eb340
    bne     a2, t0, @@msr2_other
    andi    v0, t1, 8
    move    t6, ra
    move    t5, a0
    lw      a0, 0(a1)
    lhu     v1, 0(t5)
    jal     cat_adv
    nop
    move    ra, t6
    j       0x800eb380
    move    a0, t5
@@msr2_other:
    lhu     t4, 0(a0)
    nop
    beqz    v0, 0x800eb380
    addu    v0, t4, a2
    addu    v0, t4, a3
.org 0x800eb380                 ; sh v0, 0(a0)

; Both string builders take a single-byte glyph's width field from a 0xd0-entry table,
; so Remisse's digraphs 0xd2-0xd7 (ma me wa we mo mi) read whatever heap byte follows
; it. A 7 there is the newline marker and broke "game" into "ga" + a line break.
; The field no longer sets the advance (cat_adv does), and real entries are 0-3.
.org 0x800e2bdc
    andi    v0, v0, 3
.org 0x800e97b0
    andi    v0, v0, 3
.close
