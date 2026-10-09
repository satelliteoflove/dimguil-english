; Town screens: give the main text layer 18 of the glyph sprites no layer was given.
;
; Each town screen sets up its four text layers through 0x800db3d0 (sizes for layers
; 0-3; 720 sprites in all). Most screens ask for 186, 154, 186, 114, which is 640, so 80
; sprites sat unused while layer 1 ran out. Layer 1 holds the facility name, the menus
; and the one-line help bar, and in the Inn's room list (seven lines padded with spaces
; to line up the prices) it was full at 154: the room help lines lost their ends
; ("Restores all HP for 10000G a"). Measured over every town screen, nothing allocates
; a layer outside this routine, so the spare sprites are free to use.
;
; Layer 1 gets 172 where the pool has room: the Inn's room list without its help line
; is 133 sprites, and the help bar shows about 39 glyphs. The fullest four lines the
; King or the Fortune Teller can show are 158 glyphs, plus a title of about 10. Screens
; that already ask for 703 or more (the status screen, Boltac's Trade screens) are
; unchanged. The sizes are kept in the caller's argument slots instead of s0-s3, which
; leaves room for the check; the sign-extensions of the sizes are dropped (sizes are
; small positive numbers).
.psx

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800db3d0
.area 0x800db45c - .
    addiu   sp, sp, -0x18
    sw      ra, 0x10(sp)
    sw      a0, 0x18(sp)
    sw      a2, 0x20(sp)
    sw      a3, 0x24(sp)
    addu    t0, a0, a1
    addu    t0, t0, a2
    addu    t0, t0, a3
    slti    t0, t0, 720 - 18 + 1
    beqz    t0, @@store
    move    t1, a1              ; no room: what the caller asked for
    addiu   t1, a1, 18
@@store:
    sw      t1, 0x1c(sp)
    jal     0x8001f428          ; free every layer
    addiu   a0, zero, -1
    lw      a0, 0x18(sp)
    jal     0x800dc6e0
    move    a1, zero
    lw      a0, 0x1c(sp)
    jal     0x800dc6e0
    addiu   a1, zero, 1
    lw      a0, 0x20(sp)
    jal     0x800dc6e0
    addiu   a1, zero, 2
    lw      a0, 0x24(sp)
    jal     0x8001f150
    addiu   a1, zero, 3
    lw      ra, 0x10(sp)
    nop
    jr      ra
    addiu   sp, sp, 0x18
.endarea
.close
