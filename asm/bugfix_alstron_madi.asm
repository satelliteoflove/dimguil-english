; Game bug fix: Alstron's Madi for poison, paralysis and stone (NPC_MES1 157).
;
; In Guy's handler, Alstron cures those at Guy's stages 2 and 3 if (npc_stage & 0xc) ==
; 0xc, both stage bits at once. The maze clears the old stage bit when it sets the next,
; so it was never true, and a poisoned member with full HP got "That one seems quite all
; right, I'd say." Cephala's matching check is npc_stage & 0x300 (stage 2 or 3); this
; makes Alstron's the same: either bit. docs/re/bugs.md 1.4.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800b74c8
    beq     v0, zero, 0x800b7520    ; was: bne v0, v1 (v1 = 0xc)
.close
