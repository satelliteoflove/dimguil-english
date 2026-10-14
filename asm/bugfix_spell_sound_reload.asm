; Game bug fix: a spell cast while the last spell's sound still plays can freeze the game.
;
; A spell's animation file (DATA03/MAGICnn.BIN, table 1, index 0x1bb + animation) carries
; the spell's sound sequence and its VAB header, and battle loads it into 0x801a0400 with
; load_file_alt (0x800a421c). The previous sound's sequence is still open on libsnd's
; sequence slot gp+0x2c0 and plays out of that same buffer. The game stops and closes it
; only after the new file is in (FUN_800ca890 -> MAIN 0x8001c494: SsSeqStop, SsSeqClose,
; SsVabClose, then SsSeqOpen on the new one). If the old sound is still playing while the
; new file comes in, the sequencer reads the new file's bytes as events; a tempo event of
; 0 divides by zero (MAIN 0x80029c08, break 7 at 0x80029c14), nothing handles the
; exception, and the BIOS loops in A(40h) with the screen frozen. Holding circle through
; the battle messages reaches it (Lu's Bakadi, a 271-frame sound, then Kai's Tiltowait).
; FUN_800a53fc's two loads work the same way: the encounter music (index 0x1f6 + n, into
; 0x801a0400 at 0x800a54d8) and the item tunes and chest-trap sounds (index 0x20e + n,
; into 0x801b4400 with the blocking load_file at 0x800a5534, up to 0x4000 bytes, which
; reaches the longer spell sequences at 0x801b68e0-0x801b7cc0).
;
; Each of the three loads now stops the open sequence first (SsSeqStop, MAIN 0x8002b6c0),
; through a 7-word routine in the start of FUN_800c3188, which is dead: no jal, j, branch,
; pointer word or lui/addiu pair in BATTLE or MAIN reaches it, and it never ran in the
; coverage runs. 0x8001c494 still stops and closes the sequence after the load, as
; before; a second SsSeqStop is harmless, on a stopped or a closed slot too (it only
; clears the slot's flags and keys off its voices, MAIN 0x8002b540). It only stops:
; closing here as well would close the sequence and its VAB twice. 36 words, no new
; space, no branch target among them. Chris decided on 2026-10-13 to fix it
; (docs/re/bugs.md 1.15, docs/re/decisions.md 29).
.psx
.open "dirty/dimguil/BATTLE.BIN", 0x800a1000

; The stop: SsSeqStop(gp+0x2c0) unless no sequence is open (-1). Jumps into SsSeqStop
; with the caller's ra, so SsSeqStop returns straight to the caller. Uses a0 and t0.
; Was FUN_800c3188's prologue (addiu sp, -0x40 ... sw ra, 0x3c(sp)).
.org 0x800c3188
spell_sound_stop:
    lh      a0, 0x2c0(gp)
    lui     t0, 0x8003
    bgez    a0, @@go
    addiu   t0, t0, -0x4940     ; t0 = 0x8002b6c0, SsSeqStop
    move    t0, ra              ; nothing open: just return
@@go:
    jr      t0
    nop

; Site 1, battle_main's spell animation (0x800a4200, ori a0, is a branch target and
; stays). Was: lbu a1, -0x6634(s0); addiu a2, zero, 1; sll a1, 24; sra a1, 24;
; addiu a1, 0x1bb; sll a1, 16; jal load_file_alt; sra a1, 16. lb does the 8-bit sign
; extension, and the 16-bit one is a no-op for 0x1bb + [-128, 127]. a0 is set again
; after the stop.
.org 0x800a4204
    jal     spell_sound_stop
    nop
    lui     a0, 0x801a
    ori     a0, a0, 0x400       ; 0x801a0400 again
    lb      a1, -0x6634(s0)     ; the animation number
    addiu   a2, zero, 1         ; table 1
    jal     0x80012f5c          ; load_file_alt
    addiu   a1, a1, 0x1bb

; Site 2, FUN_800a53fc's encounter music (0x800a54c0 and 0x800a5520 are branch targets;
; nothing between them is). 0x800a54c8-0x800a54e8 and 0x800a5510 change. The two words
; come from the second lui v1, 0x800e at 0x800a5510 (v1 still holds it) and from moving
; li s1, 0xa0 (was 0x800a54e8) into the load delay that lui filled; nothing reads s1 in
; between.
.org 0x800a54c8
    jal     spell_sound_stop
    andi    s0, s0, 0xff        ; s0 survives the call
    lui     a0, 0x801a
    ori     a0, a0, 0x400
    addiu   a2, zero, 1
    jal     0x80012f5c          ; load_file_alt
    addiu   a1, s0, 0x1f6
    lui     a0, 0x801a
    ori     a0, a0, 0x400
    lui     v0, 0x800e          ; from here to the end, as before but for one word
    addiu   v0, v0, -0x7e5c
    sll     s0, s0, 3
    addu    s0, s0, v0
    lw      v0, 0(s0)
    lui     v1, 0x800e
    addu    v0, v0, a0
    sw      v0, -0x58f8(v1)
    lw      v0, 4(s0)
    addiu   s1, zero, 0xa0      ; was lui v1, 0x800e
    addu    v0, v0, a0
    j       0x800a5588
    sw      v0, -0x58f4(v1)

; Site 3, FUN_800a53fc's item tune or chest-trap sound (0x800a5520 and 0x800a5580 are
; branch targets and stay). 0x800a5524-0x800a5548, 0x800a5578 and 0x800a557c change.
; The two words come from a1 taking v1 (both were 0x801b4400, by their own lui/ori) and
; from the second lui v0, 0x800e at 0x800a5578 (v0 still holds it); the last word is a
; nop before the jal 0x8001c494 at 0x800a5580.
.org 0x800a5524
    jal     spell_sound_stop
    andi    s0, s0, 0xff
    lui     a0, 0x801b
    ori     a0, a0, 0x4400
    addiu   a1, s0, 0x20e
    jal     0x80012d18          ; load_file
    addiu   a2, zero, 1
    lui     v1, 0x801b
    ori     v1, v1, 0x4400
    move    a1, v1              ; was lui a1, 0x801b; ori a1, 0x4400
    lui     v0, 0x800e          ; from here as before but for the last two words
    addiu   v0, v0, -0x7d9c
    sll     s0, s0, 3
    addu    s0, s0, v0
    addiu   s1, zero, 0xa4
    lui     v0, 0x800e
    lw      a0, 0(s0)
    lw      a2, 4(s0)
    addu    a0, a0, v1
    addu    a2, a2, v1
    sw      a0, -0x58f8(v0)
    sw      a2, -0x58f4(v0)     ; was lui v0, 0x800e
    nop                         ; was sw a2, -0x58f4(v0)

.close
