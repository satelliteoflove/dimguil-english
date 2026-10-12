; Reopened content: Zaril's party offers healing (NPC_MES5 35-42, 114).
;
; NPC_MES5 holds a whole healing exchange for Zaril and the log line "We asked them for
; healing.", but his handler (talk_zaril, MCARD 0x800d9b34) has no heal offer and no heal
; states, so none of it ever played. Chris approved reopening it (2026-10-11): Zaril is a
; Dracon Lord, and his lines name Priest spells.
;
; Copied from the other party handlers (talk_guy, talk_balbo), adding nothing they don't do:
; - Talk, with everyone introduced: Zaril's sale roll runs first, exactly as before. Only
;   when it doesn't fire (where the original goes on to a chat topic) and a member has a
;   status or HP at or under max/5, a 50% service roll and then a 50% heal roll (25% per
;   check, as for the other parties) offer healing (state 0x2d). So his sale keeps its
;   original odds; healing comes up 25% of the time when no sale can be offered, and 12.5%
;   when one could (50% no sale x 25%).
; - The offer, then the shared member picker (state 0x32), then the result (0x37). One
;   healer, so no 50/50 between two. His lines match Guy's and Balbo's stage-3 table:
;   healthy (5:36) and "can't" (5:37, stone/dead/ashes) let you pick again; 20% out of
;   spells (5:40); paralysis Dialko (5:38, cure 1); poison Latumofis (5:39, cure 3); hurt
;   Dialma (5:41, cure 4); cancel (5:42). As in the others, any outcome but healthy uses
;   up Talk for this meeting (talk_menu bit 0).
;
; Hooks: talk_zaril's state dispatch (0x800da4b8) and the store of the chat state after
; the sale roll (0x800daae0), which all four no-sale paths reach. Space: the unreferenced routines at 0x800b4100 (a
; yes/no box) and 0x800ab09c-0x800ab1cb (two card-status checks), and the rest of the
; unused debug routine after the pit fixes (0x800c5820-0x800c58db, through FUN_800c589c,
; also unreferenced). docs/re/bugs.md 2.2.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800da4b8                 ; state dispatch, was: lh v1, talk_state(s0) (next: nop)
    j       zaril_states

.org 0x800daae0                 ; no sale, was: sh v0 (0x28), talk_state(v1) (next: lui v0, 0x8008)
    j       zaril_offer

; The states. s0 = 0x80080000 here; every exit goes to the handler's epilogue, which
; restores the saved registers.
.org 0x800b4100
.area 0x800b42d0 - .
zaril_states:
    lh      v1, -0x67e4(s0)         ; talk_state
    addiu   t9, zero, 0x2d
    beq     v1, t9, @@offer
    addiu   t9, zero, 0x32
    beq     v1, t9, @@pick
    addiu   t9, zero, 0x37
    beq     v1, t9, @@result
    nop
    bnez    v1, @@other             ; the original dispatch, as it was
    addiu   s3, s0, -0x67e4
    j       0x800da4c8              ; state 0
    nop
@@other:
    j       0x800da4fc
    nop

@@pick:                             ; 0x32: wait for the picker (2 picked, 3 cancelled)
    lb      v1, -0x6a9a(s0)         ; 0x80079566
    addiu   v0, zero, 3
    bne     v1, v0, @@picked
    addiu   v0, zero, 2
    sb      zero, -0x6a9a(s0)
    j       @@to_result_spent
    addiu   t1, zero, 7             ; cancelled
@@picked:
    bne     v1, v0, @@ret
    lb      v1, -0x65a6(s0)         ; camp_char
    sb      zero, -0x6a9a(s0)
    sll     v0, v1, 1
    addu    v0, v0, v1
    sll     v0, v0, 2
    addu    v0, v0, v1
    sll     v0, v0, 4               ; * 0xd0
    addu    v0, v0, s0
    addiu   s1, v0, -0x28f8         ; roster[camp_char] (0x8007d708)
    lh      s2, 0x46(s1)            ; HP
    lh      s3, 0x4a(s1)            ; max HP
    lhu     s4, 0xe(s1)             ; status
    bne     s2, s3, @@needs_it
    nop
    beqz    s4, @@to_result
    addiu   t1, zero, 1             ; nothing wrong: pick again
@@needs_it:
    jal     0x8001cb18              ; rand_upto(99)
    addiu   a0, zero, 99
    slti    v0, v0, 20
    bnez    v0, @@to_result_spent
    addiu   t1, zero, 2             ; 20%: out of spells
    andi    v0, s4, 0x1c0
    bnez    v0, @@to_result_spent
    addiu   t1, zero, 3             ; stone, dead or ashes: can't, pick again
    andi    v0, s4, 0x20
    bnez    v0, @@to_result_spent
    addiu   t1, zero, 4             ; paralysis: Dialko
    andi    v0, s4, 4
    bnez    v0, @@to_result_spent
    addiu   t1, zero, 5             ; poison: Latumofis
    slt     v0, s2, s3
    bnez    v0, @@to_result_spent
    addiu   t1, zero, 6             ; hurt: Dialma
    j       @@to_result
    addiu   t1, zero, 1             ; nothing he can treat: as healthy
@@to_result_spent:
    lbu     v0, -0x64b0(s0)         ; talk_menu
    nop
    andi    v0, v0, 0xfe            ; Talk is used up for this meeting
    sb      v0, -0x64b0(s0)
@@to_result:
    sb      t1, -0x644c(s0)         ; talk_block
    addiu   v0, zero, 0x37
    j       @@ret
    sh      v0, -0x67e4(s0)

@@result:                           ; 0x37: play the outcome
    lb      v0, -0x644c(s0)
    la      a0, zaril_heal_scripts
    sll     v1, v0, 5
    sll     v0, v0, 2
    subu    v1, v1, v0
    jal     0x800b8ccc
    addu    a0, a0, v1
    lh      v1, -0x675c(s0)
    addiu   v0, zero, -1
    bne     v1, v0, @@ret
    lb      v1, -0x644c(s0)
    addiu   v0, zero, 1
    beq     v1, v0, @@again         ; nothing wrong: pick again
    addiu   v0, zero, 3
    beq     v1, v0, @@again         ; can't: pick again
    addiu   v0, zero, 10
    sh      v0, -0x67e4(s0)         ; back to the menu
    j       @@ret
    sh      zero, -0x675c(s0)
@@again:
    sb      zero, -0x6820(s0)       ; 0x800797e0
    j       @@picker_on
    sb      zero, -0x644c(s0)       ; talk_block = 0
@@offer:                            ; 0x2d: the offer, then the member picker
    lb      v0, -0x644c(s0)         ; talk_block
    la      a0, zaril_heal_scripts
    sll     v1, v0, 5
    sll     v0, v0, 2
    subu    v1, v1, v0              ; talk_block * 28
    jal     0x800b8ccc              ; talk_script_run
    addu    a0, a0, v1
    lh      v0, -0x66c8(s0)         ; glyph_layer_used
    lhu     v1, -0x68e8(s0)         ; 0x80079718
    bnez    v0, @@offer_wait
    nop
    sh      v1, -0x66c8(s0)
@@offer_wait:
    lh      v1, -0x675c(s0)         ; talk_script_status
    addiu   v0, zero, -1
    bne     v1, v0, @@ret
    nop
@@picker_on:
    addiu   v0, zero, 1
    sb      v0, -0x6a9a(s0)         ; picker on
    sb      v0, -0x6934(s0)         ; its cursor: column 1
    sb      zero, -0x6933(s0)       ; row 0
    sh      zero, -0x65da(s0)       ; talk_script_pos
    sh      zero, -0x675c(s0)       ; talk_script_status
    addiu   v0, zero, 0x32
    sh      v0, -0x67e4(s0)
@@ret:
    j       0x800db700              ; talk_zaril's epilogue
    nop
.endarea

; The scripts, 28 bytes a block: opcodes as in talk_script_run (0x800b8ccc). Zaril is
; character 10; his expressions are 0 plain, 2 annoyed, 3 sorry, as his other lines use them.
.org 0x800ab09c
.area 0x800ab1cc - .
zaril_heal_scripts:
    .halfword 7,114, 6,10, 0,10,109, 3,10,0,109, 2,35, -1   ; 0 bar, load, show, offer
    .halfword 3,10,2,109, 2,36, -1, 0,0,0,0,0,0,0           ; 1 nothing wrong
    .halfword 3,10,3,109, 2,40, -1, 0,0,0,0,0,0,0           ; 2 out of spells
    .halfword 3,10,3,109, 2,37, -1, 0,0,0,0,0,0,0           ; 3 can't cure this one
    .halfword 3,10,0,109, 2,38, 9,1, -1, 0,0,0,0,0          ; 4 Dialko
    .halfword 3,10,0,109, 2,39, 9,3, -1, 0,0,0,0,0          ; 5 Latumofis
    .halfword 3,10,0,109, 2,41, 9,4, -1, 0,0,0,0,0          ; 6 Dialma
    .halfword 3,10,0,109, 2,42, -1, 0,0,0,0,0,0,0           ; 7 declined
.endarea

; The offer, on Talk once everyone is introduced, when the sale roll didn't fire.
.org 0x800c5820
.area 0x800c58dc - .
zaril_offer:
    lui     t0, 0x8008
    addiu   t0, t0, -0x17ee         ; party slots, 0x8007e812
    addiu   t2, t0, 6
@@scan:                             ; anyone with a status, or HP at or under max/5?
    lb      v1, 0(t0)
    addiu   t0, t0, 1
    bltz    v1, @@next              ; empty slot
    sll     v0, v1, 1
    addu    v0, v0, v1
    sll     v0, v0, 2
    addu    v0, v0, v1
    sll     v0, v0, 4
    lui     t1, 0x8008
    addu    v0, v0, t1
    lhu     t1, -0x28f8+0xe(v0)     ; status
    lh      t3, -0x28f8+0x46(v0)    ; HP
    bnez    t1, @@hurt
    lh      t4, -0x28f8+0x4a(v0)    ; max HP
    addiu   t5, zero, 5
    div     t4, t5
    mflo    t5
    slt     v0, t5, t3
    beqz    v0, @@hurt
    nop
@@next:
    bne     t0, t2, @@scan
    nop
@@resume:                           ; no offer: on to a chat topic, as the original
    lui     v1, 0x8008
    addiu   v0, zero, 0x28
    j       0x800daae4
    sh      v0, -0x67e4(v1)         ; talk_state = 0x28
@@hurt:
    jal     0x8001cb18              ; rand_upto(1): the 50% service roll
    addiu   a0, zero, 1
    beqz    v0, @@resume
    nop
    jal     0x8001cb18              ; rand_upto(1): the 50% heal roll
    addiu   a0, zero, 1
    bnez    v0, @@resume
    lui     v1, 0x8008
    sb      zero, -0x644c(v1)       ; talk_block = 0
    sh      zero, -0x68e8(v1)       ; 0x80079718
    addiu   v0, zero, 1
    sb      v0, -0x6878(v1)         ; 0x80079788
    addiu   v0, zero, 0x2d
    j       0x800db700
    sh      v0, -0x67e4(v1)         ; talk_state = 0x2d
.endarea
.close
