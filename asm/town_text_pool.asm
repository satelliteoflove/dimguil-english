; Town screens: give the main text layer the glyph sprites no layer was given.
;
; Each town screen sets up its four text layers through 0x800db3d0 (sizes for layers
; 0-3; 720 sprites in all). Most screens ask for 186, 154, 186, 114, which is 640, so 80
; sprites sat unused while layer 1 ran out. Layer 1 holds the facility name, the menus
; and the one-line help bar, and in the Inn's room list (seven lines padded with spaces
; to line up the prices) it was full at 154: the room help lines lost their ends
; ("Restores all HP for 10000G a"). Measured over every town screen, nothing allocates
; a layer outside this routine, so the spare sprites are free to use.
;
; This rewrites the routine with the same calls, but layer 1 gets 720 minus the other
; three, so screens that already use the whole pool (the status screen, Boltac's Trade
; screens) are unchanged. The sign-extensions of the sizes are dropped; sizes are
; small positive numbers.
.psx

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800db3d0
    addiu   sp, sp, -0x28
    sw      s0, 0x10(sp)
    sw      s1, 0x14(sp)
    sw      s2, 0x18(sp)
    sw      s3, 0x1c(sp)
    sw      ra, 0x20(sp)
    move    s0, a0
    move    s2, a2
    move    s3, a3
    addu    t0, a0, a2
    addu    t0, t0, a3
    addiu   s1, zero, 720
    subu    s1, s1, t0          ; layer 1: what the other three leave (was a1)
    jal     0x8001f428          ; free every layer
    addiu   a0, zero, -1
    move    a0, s0
    jal     0x800dc6e0
    move    a1, zero
    move    a0, s1
    jal     0x800dc6e0
    addiu   a1, zero, 1
    move    a0, s2
    jal     0x800dc6e0
    addiu   a1, zero, 2
    move    a0, s3
    jal     0x8001f150
    addiu   a1, zero, 3
    nop
.if org() != 0x800db440
    .error "town_text_pool: the rewrite must end where the original's epilogue starts"
.endif
.close
