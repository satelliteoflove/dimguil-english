; Game bug fix: the pit scene no longer locks up when nobody has met Guy.
;
; talk_scene_pit (handler 21) picks the rescuer in state 0xf. With npc_flags bit 7 clear
; it's Balbo (block 3) if a member has met Balbo, else the man in armor (block 4). With
; bit 7 set (from first entering areas 0x13-0x16 until Guy gets the Ruby Slippers) it's
; Guy (block 2), but only if a member has met Guy; if nobody has, no block is picked,
; talk_block keeps the block that just played, and state 0x14 replays it. That block ends
; with "end", not "close", so the talk never finishes: the screen sits on Fontana's
; portrait with an empty window for good (seen in the emulator on our build and on the
; original MCARD).
;
; Now, when the Guy loop picks nobody, state 0xf falls through to the bit-7-clear choice,
; the game's own rescuer for a party that isn't Guy's acquaintance. Guy has no stranger
; version, and his block 2 ("Besides, I owed you one") assumes an introduction.
;
; The Guy loop's exit (j to the state-0x14 store) jumps to a few lines in the unused debug
; routine at MCARD 0x800c57c8, after bugfix_pit_scene.asm's code there. docs/re/bugs.md 2.8.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800d649c                 ; Guy loop done, was: j 0x800d6538 (delay slot: lui v1, 0x8008)
    j       pit_rescuer

.org 0x800c5800
.area 0x800c5820 - .             ; bugfix_zaril_heal.asm follows
pit_rescuer:                    ; v1 = 0x80080000 (set in the delay slot)
    lb      v0, -0x644c(v1)     ; talk_block
    addiu   a1, zero, 2         ; (a1 is set again by either loop)
    beq     v0, a1, @@guy       ; a member has met Guy: block 2, as before
    nop
    j       0x800d64b4          ; nobody has: Balbo or the man in armor
    move    a0, zero            ; that loop's counter, as the bit-7 test's delay slot sets it
@@guy:
    j       0x800d6538          ; talk_state = 0x14 (needs v1 = 0x80080000)
    nop
.endarea
.close
