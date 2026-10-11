; Game bug fix: the pit scene plays its middle (NPC_MES3 95-96, 99-100).
;
; talk_scene_pit (handler 21) builds five script blocks every frame: 0 the fall and
; Fontana's (or the young samurai's) first lines, 1 the voice from above and "Looks like
; help has arrived. If you'll excuse us, we'll go on ahead.", 2-4 the rescuer. State 5
; plays talk_block, and when it ends goes to state 10, which went straight to 0xf, where
; the rescuer is picked. Block 1 was built, with its strings filled in, and never run.
;
; Now state 10 runs block 1 first: if talk_block is 0 it becomes 1 and the scene goes
; back to state 5 (script position and status were already reset there); after block 1,
; state 10 goes on to 0xf as before.
;
; State 10's code had one spare instruction (the delay slot of its bne already loads
; v0 = 0xf, and the next instruction loaded it again), so it jumps to a few lines placed
; over MCARD 0x800c57c8: an unreferenced debug routine (an encounter-id picker drawn with
; FntPrint) that no call, pointer or computed address reaches. docs/re/bugs.md 1.5.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800d63f0                 ; state 10, was: addiu v0, zero, 0xf / j 0x800d6598 / sh v0, talk_state
    j       pit_state10
    nop
    nop

.org 0x800c57c8
.area 0x800c589c - .
pit_state10:                    ; v0 = 0xf, s0 = 0x80080000
    lui     v1, 0x8008
    lb      a0, -0x644c(v1)     ; talk_block
    nop
    bne     a0, zero, @@store   ; block 1 has played: on to the rescuer (0xf)
    nop
    addiu   a0, zero, 1
    sb      a0, -0x644c(v1)     ; talk_block = 1
    addiu   v0, zero, 5         ; play it
@@store:
    j       0x800d6598
    sh      v0, -0x67e4(s0)     ; talk_state
.endarea
.close
