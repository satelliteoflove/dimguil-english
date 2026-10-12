; Reopened content: Fontana's chat about Zaril's new party (NPC_MES3 197, 199-200,
; talk_fontana chat block 8).
;
; Block 8 is a whole chat script, Fontana ("Zaril, who used to be with us, has formed a
; party of his own...") and Cephala ("We met Zaril's party..."), but no code picks it.
; Chris approved adding it (2026-10-11), only after the party splits: the split scene
; (handler 20) moves Fontana to stage 3 (npc_stage 0x200, with 0x80 and 0x100 cleared),
; and Zaril leaves in it.
;
; Fontana's chat (state 0x28): an area special at areas 0x20-0x23, or at stage 1 one of
; seven "other parties" specials, each kept 90% of the time; otherwise rand_upto(7) picks
; one of eight topics, each played as its stage-1/2 or stage-3 block. Block 8 joins that
; roll as a ninth topic at stage 3 only: rand_upto(8) there, with 8 meaning block 8. Each
; of the eight topics goes from 1/8 to 1/9 of the rolls at stage 3 (12.5% to 11.1%), and
; block 8 gets 1/9; nothing changes at stages 1 and 2, or for the area special. Stage 3
; is tested the way the topic code tests it: (npc_stage & 0x180) == 0 and & 0x200.
;
; Hook: the topic roll (0x800d13b4). The code sits in the never-run blocks of Cresson's
; chat array, after the re-introductions. docs/re/bugs.md 2.5.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800d13b4                 ; was: jal rand_upto (delay slot: addiu a0, zero, 7, kept)
    j       fontana_topic

.org 0x800a8200
.area 0x800a8280 - .
fontana_topic:                  ; s0 = 0x80080000
    lui     v0, 0x8008
    lw      v1, -0x69e8(v0)     ; npc_stage
    nop
    andi    t0, v1, 0x180
    bnez    t0, @@eight         ; stage 1 or 2: the eight topics, as before
    andi    t0, v1, 0x200
    beqz    t0, @@eight
    nop
    jal     0x8001cb18          ; stage 3: rand_upto(8), nine topics
    addiu   a0, zero, 8
    addiu   t0, zero, 8
    bne     v0, t0, @@back
    nop
    sb      v0, -0x644c(s0)     ; talk_block 8: Zaril's new party
    j       0x800d1d68          ; talk_script_status = 0, return
    nop
@@eight:
    jal     0x8001cb18          ; rand_upto(7), as the original
    addiu   a0, zero, 7
@@back:
    j       0x800d13bc          ; store talk_block and play the topic's block for the stage
    nop
.endarea
.close
