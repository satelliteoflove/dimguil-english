; Word wrap for wrapped messages (battle text and the like).
;
; 0x8001dfc0 expands a message into the buffer at 0x8008b400. With wrapping on (s4), it
; moves an inserted name to a new line when the whole name won't fit, but plain text
; only gets a column count: after the 24th code it breaks, mid-word if need be
; ("Jupiter sweeps Cuautori wi / th LANCE."). Whether that happens depends on the
; lengths of the names in the line, so no placement of line breaks in the templates
; can avoid it.
;
; This gives plain text a lookahead: after a space, the next word is measured in the
; source (up to the next space or control code) and, if it won't fit, the line breaks
; there. Twelve digraph codes end in a space ("e ", "s ", ", " and so on); they end a
; word too, and the break goes after them. Otherwise the old rule stands: break once
; the line is full.
;
; Every automatic break replaces a plain space just before it, so no line ends in one.
; Before, the break before a name went in after the space ("Xicalli whips Venus with /
; vines.", half a space left of center).
;
; A digraph ending in a space just before an automatic break is rewritten as its letter
; alone ("A " becomes "A"), so its space doesn't end the line either: "Giant Ant calls
; for help! A / monster appears." sat 2 px left of center, and 25 FIGHTMSG strings can
; break after such a digraph (fightfit.py --digraphs). The letter is one glyph code, like
; the digraph, so the expander's column, the battle box's per-line glyph count and the
; sprites drawn all stay as they were; only the line's width shrinks by the space. The
; measure and the drawing both read this buffer, so they see the same code. Everything
; is in MAIN, with the expander.
;
; Every break in plain text also drops a plain space that comes straight after it in the
; source. Without that, a word that fills the line exactly ("...Xicalli with") left the
; following space to start the next line (" BLOW GUN."), one half-space off center.
;
; A full line in plain text doesn't break when the source's next code is {ff21}: that
; explicit break ends the line itself. Before, both went in and left an empty line
; ("Earth dispels Noisy Tempter." / "" / "(4 destroyed)", FIGHTMSG 106). The end of the
; message, {ff40}, needs nothing: the original takes an automatic break back off there
; (0x8001e418). Room: @check now loads the source pointer in its branch's delay slot,
; for break_at, with one branch on both conditions.
;
; The function has three inline copies of its "write {ff21}" sequence at 21
; instructions each. All three now go through one routine, write_break, which returns
; through t7 (the original function uses no t registers, and nothing it calls runs
; between setting t7 and the jr). That makes room for the helpers. The digraph rule
; took the rest: the name path's check before write_break lost two nops and a lui
; (0x8001e164), and the table of letters sits where the name copy tested for the 12 px
; font and a voicing mark (0x8001e2b0), a test voicing_marks.asm had made always say no.
;
; Registers here: a0 = the byte just read, s0 = column, s1 = buffer, s2 = 0x21,
; s3 = 0xff, s4 = wrap flag, a3 = end flag (preserved). Globals (0x8008xxxx):
; -0x676e buffer position (h), -0x6938 line limit (b), -0x6614 source pointer (w),
; -0x6914 the inserted name's length (b).
; ra is free: the function saved it, and calls 0x8001e498 itself.
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800

SPACE equ 0xba
LETTERS_FIRST equ 0x8b      ; the table covers 0x8b-0xb7
LETTERS_COUNT equ 45

; Break before a name that won't fit (was 21 instructions). The check is the original's,
; with t0 and t7 set in what were two nops and a second lui.
.org 0x8001e164
.area 0x8001e1f0-.
    beqz    s4, 0x8001e1f0          ; not wrapping
    lui     t0, 0x8008
    lbu     v0, -0x6914(t0)         ; the name's length
    lb      v1, -0x6938(t0)         ; line limit
    lui     t7, hi(0x8001e1f0)
    addu    v0, s0, v0
    sll     v0, v0, 0x18
    sra     v0, v0, 0x18
    slt     v1, v1, v0
    beqz    v1, 0x8001e1f0          ; it fits
    sll     v0, s0, 0x18
    beqz    v0, 0x8001e1f0          ; column 0: it starts the line anyway
    addiu   t7, t7, lo(0x8001e1f0)

; Write {ff21} at the buffer position, set the column to 0 and return to t7. A plain
; space just before the position goes: the break takes its place. A digraph ending in a
; space just before it becomes its letter. Every caller has s0 > 0, so that byte is on
; the current line. Two-byte glyphs (0xf7-0xfe and a second byte) can't reach battle
; text: names are typed on single-byte grids, and nothing in FIGHTMSG or the name lists
; encodes to them.
write_break:
    lui     t0, 0x8008
    lh      v0, -0x676e(t0)         ; position
    move    s0, zero
    addu    v1, v0, s1
    lbu     t8, -1(v1)              ; the byte before
    addiu   v0, v0, 2               ; position after the {ff21}
    addiu   t9, t8, -LETTERS_FIRST
    xori    t8, t8, SPACE
    sltiu   t5, t9, LETTERS_COUNT
    beqz    t5, @@space
    sltiu   t8, t8, 1               ; 1 = a plain space
    lui     t5, hi(letters)         ; 0x8b-0xb7: no plain space, so the {ff21} goes
    addu    t5, t5, t9              ; at the position
    lbu     t5, lo(letters)(t5)
    b       @@write
    sb      t5, -1(v1)              ; a digraph's letter; any other code as it was
@@space:
    subu    v1, v1, t8
    subu    v0, v0, t8
@@write:
    sb      s3, 0(v1)
    sb      s2, 1(v1)
    jr      t7
    sh      v0, -0x676e(t0)
.endarea

; Name copy, a one-byte glyph: count it, unless it's 0xff (was 15 instructions). The
; original skipped a voicing mark here in the 12 px font; voicing_marks.asm had made
; that test always say no, so every one-byte glyph below 0xf8 was counted already.
.org 0x8001e2a4
.area 0x8001e2e0-., 0
    sltiu   v0, v1, 0xf8            ; v1 = the byte (lbu at 0x8001e250)
    b       0x8001e2e0
    addu    s0, s0, v0

; Codes 0x8b-0xb7 at a break: each digraph ending in a space as its letter, the rest
; unchanged (the Ancient letters 0x93-0xac, ( ) + UP DOWN of ").
letters:
    ;   ,     e     s     d     t     n     r     y           (0x8b-0x92)
    .db 0xc7, 0x29, 0x37, 0x28, 0x38, 0x32, 0x36, 0x3d
    .db 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f
    .db 0xa0, 0xa1, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xab, 0xac
    ;   g     .                       A                             w   (0xad-0xb7)
    .db 0x2b, 0xc2, 0xaf, 0xb0, 0xb1, 0x0b, 0xb3, 0xb4, 0xb5, 0xb6, 0x3b
.if . - letters != LETTERS_COUNT
    .error "the letter table must cover 0x8b-0xb7"
.endif
.endarea

; Break inside a name that runs past the line (was 21 instructions).
.org 0x8001e2fc
.area 0x8001e350-., 0       ; the rest is nop
    lui     t7, hi(0x8001e350)
    j       write_break
    addiu   t7, t7, lo(0x8001e350)

; Plain text: break and carry on (t0 = 0x80080000, t3 = the source pointer). A plain
; space next in the source is skipped, so it can't start the new line. {ff21} next: no
; break, it makes its own (s3 = 0xff, s2 = 0x21).
break_at:
    lui     t7, hi(0x8001e410)
    lbu     t4, 0(t3)               ; source: the next byte
    lbu     t5, 1(t3)               ; and the one after
    bne     t4, s3, @@nobreak
    xori    t4, t4, SPACE
    beq     t5, s2, 0x8001e410      ; {ff21}: no automatic break
@@nobreak:
    addiu   t3, t3, 1               ; (beq's delay slot, harmless when taken)
    bnez    t4, write_break
    addiu   t7, t7, lo(0x8001e410)
    j       write_break
    sw      t3, -0x6614(t0)         ; a plain space: skip it

; t5 = nonzero if code t4 is a space or a digraph ending in one (0x8b-0x92, 0xad, 0xae,
; 0xb2, 0xb7, and 0xba itself). Uses t9 only.
is_space:
    addiu   t9, t4, -0xad
    sltiu   t5, t9, 14
    beqz    t5, is_space_low
    addiu   t5, zero, 0x2423        ; bits 0, 1, 5, 10, 13 = 0xad, 0xae, 0xb2, 0xb7, 0xba
    srlv    t5, t5, t9
    jr      ra
    andi    t5, t5, 1
.endarea

; Plain text (a0 < 0xf0).
.org 0x8001e370
.area 0x8001e410-.
    lui     t0, 0x8008
    lh      v0, -0x676e(t0)         ; position
    lb      t1, -0x6938(t0)         ; line limit
    addu    v1, v0, s1
    sb      a0, 0(v1)               ; write the character
    addiu   v0, v0, 1
    beqz    s4, 0x8001e410          ; not wrapping
    sh      v0, -0x676e(t0)
    addiu   s0, s0, 1               ; column
    jal     is_space
    move    t4, a0
    beqz    t5, @check
    move    t2, s0                  ; t2 = column after the next word
    lw      t3, -0x6614(t0)         ; source: the next word
    nop                             ; (load delay)
@scan:
    lbu     t4, 0(t3)
    addiu   t3, t3, 1
    sltiu   t5, t4, 0xf0
    beqz    t5, @wide
    addiu   t2, t2, 1               ; count it
    jal     is_space
    xori    t8, t4, SPACE
    beqz    t5, @scan               ; inside the word
    sltiu   t8, t8, 1
    b       @check                  ; end of word; a plain space isn't part of it
    subu    t2, t2, t8

; The rest of is_space (no room for it there; reached only by its branch).
is_space_low:
    addiu   t9, t4, -0x8b
    jr      ra
    sltiu   t5, t9, 8

@wide:
    sltiu   t5, t4, 0xf7
    bnez    t5, @uncount            ; 0xf0-0xf6: stop
    sltiu   t5, t4, 0xff
    bnez    t5, @scan               ; 0xf7-0xfe: two-byte glyph, skip its second byte
    addiu   t3, t3, 1
@uncount:
    addiu   t2, t2, -1              ; a control code isn't part of the word
@check:
    slt     t5, s0, t1              ; 0 = line full
    slt     t6, t1, t2              ; 1 = next word won't fit
    sltu    t5, t6, t5              ; 1 = neither
    beqz    t5, break_at
    lw      t3, -0x6614(t0)         ; source pointer, for break_at (unused otherwise)
.if . != 0x8001e410
    .error "the plain-text path must fall through to 0x8001e410"
.endif
.endarea

.close
