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
; there. A plain space becomes the break itself. Twelve digraph codes end in a space
; ("e ", "s ", ", " and so on); they end a word too, and the break goes after them.
; Otherwise the old rule stands: break once the line is full.
;
; The function has three inline copies of its "write {ff21}" sequence at 21
; instructions each. The two in the name path are compacted, which makes room for the
; helpers.
;
; Registers here: a0 = the byte just read, s0 = column, s1 = buffer, s2 = 0x21,
; s3 = 0xff, s4 = wrap flag, a3 = end flag (preserved). Globals (0x8008xxxx):
; -0x676e buffer position (h), -0x6938 line limit (b), -0x6614 source pointer (w).
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800

SPACE equ 0xba

; Break before a name that won't fit (was 21 instructions).
.org 0x8001e19c
.area 0x8001e1f0-.
    lui     t0, 0x8008
    lh      v0, -0x676e(t0)
    nop
    addu    v1, v0, s1
    sb      s3, 0(v1)
    sb      s2, 1(v1)
    addiu   v0, v0, 2
    sh      v0, -0x676e(t0)
    j       0x8001e1f0
    move    s0, zero

; t5 = nonzero if code t4 is a space or a digraph ending in one (0x8b-0x92, 0xad, 0xae,
; 0xb2, 0xb7, and 0xba itself). Uses t9 only.
is_space:
    addiu   t9, t4, -0xad
    sltiu   t5, t9, 14
    beqz    t5, @@low
    addiu   t5, zero, 0x2423        ; bits 0, 1, 5, 10, 13 = 0xad, 0xae, 0xb2, 0xb7, 0xba
    srlv    t5, t5, t9
    jr      ra
    andi    t5, t5, 1
@@low:
    addiu   t9, t4, -0x8b
    jr      ra
    sltiu   t5, t9, 8
.endarea

; Break inside a name that runs past the line (was 21 instructions).
.org 0x8001e2fc
.area 0x8001e350-.
    lui     t0, 0x8008
    lh      v0, -0x676e(t0)
    nop
    addu    v1, v0, s1
    sb      s3, 0(v1)
    sb      s2, 1(v1)
    addiu   v0, v0, 2
    sh      v0, -0x676e(t0)
    j       0x8001e350
    move    s0, zero

; Plain text: write {ff21} at t6 and carry on (t0 = 0x80080000).
break_at:
    sb      s3, 0(t6)
    sb      s2, 1(t6)
    subu    v0, t6, s1
    addiu   v0, v0, 2
    sh      v0, -0x676e(t0)
    j       0x8001e410
    move    s0, zero
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
    addiu   t6, v1, 1               ; a break goes after the character
    jal     is_space
    move    t4, a0
    beqz    t5, @@check
    move    t2, s0                  ; t2 = column after the next word
    lw      t3, -0x6614(t0)         ; source: the next word
    xori    t8, a0, SPACE
    sltiu   t8, t8, 1
    subu    t6, t6, t8              ; a plain space: the break replaces it
@@scan:
    lbu     t4, 0(t3)
    addiu   t3, t3, 1
    sltiu   t5, t4, 0xf0
    beqz    t5, @@wide
    addiu   t2, t2, 1               ; count it
    jal     is_space
    xori    t8, t4, SPACE
    beqz    t5, @@scan              ; inside the word
    sltiu   t8, t8, 1
    b       @@check                 ; end of word; a plain space isn't part of it
    subu    t2, t2, t8
@@wide:
    sltiu   t5, t4, 0xf7
    bnez    t5, @@uncount           ; 0xf0-0xf6: stop
    sltiu   t5, t4, 0xff
    bnez    t5, @@scan              ; 0xf7-0xfe: two-byte glyph, skip its second byte
    addiu   t3, t3, 1
@@uncount:
    addiu   t2, t2, -1              ; a control code isn't part of the word
@@check:
    slt     t5, s0, t1
    beqz    t5, break_at            ; line full
    slt     t5, t1, t2
    bnez    t5, break_at            ; next word won't fit
    nop
.if . != 0x8001e410
    .error "the plain-text path must fall through to 0x8001e410"
.endif
.endarea

.close
