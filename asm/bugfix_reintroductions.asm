; Reopened content: Guy's and Fontana's parties re-introduce themselves (NPC_MES1 134-139,
; NPC_MES3 117-123).
;
; Balbo's, Cresson's and Zaril's handlers have three cases on Talk: nobody in the party has
; met the leader (the full introductions), only some have (a short "didn't we do this
; already?" re-introduction), and everyone has (services and chat). Guy's and Fontana's
; handlers lack the middle case, though both files have its lines:
; - Guy (talk_guy) plays the full introductions whenever anyone hasn't met him.
; - Fontana (talk_fontana) plays them only when nobody has met him; with some met, the
;   newcomers are never introduced at all.
; Chris approved adding the branch (2026-10-11). Modeled on Balbo's (talk_balbo state 0x1e):
; count the members who haven't met the leader; all of them: the introductions, as before;
; some: the re-introduction; none: services and chat, as before.
;
; The re-introduction scripts follow the stage's introduction script: the same members in
; the same places, each saying their "again" line instead. Guy's lines name only the
; first four of his party (134 Guy, 135 Alstron, 136 Linaria, 137-139 Lychee), so his is one
; block for every stage; Fritillaria and Lilia, who join later, keep their own
; self-introductions in Guy's greetings (1:140, 1:141). Fontana's has a block per stage,
; as Balbo's does: stage 1 Fontana, Zaril, Artemisia, Lilia, Cephala; stage 2 without
; Zaril; stage 3 Fontana, Cephala, Reiran. Opcode 0 (show) sets each shown character's met
; bit for every member during state 0x23, so the newcomers are marked met just as the full
; introductions mark them. The second Guy line-up (1:128-133) stays unplaced: see
; docs/re/bugs.md 2.3.
;
; Expressions: the introduction's, except where the line's mood differs; then the one the
; character uses for that mood elsewhere (Guy 3 as in "what the heck happened to this
; maze?", Linaria 3, Lychee 1 surprised and 5 "Ehehe", Fontana 3, Lilia 3 then 1, Cephala 1),
; and for Artemisia and Reiran, the ones Balbo's re-introduction gives the same lines
; (2:113, 2:111).
;
; Space: the never-run blocks 19-24 of Cresson's chat array (0x800a7e14-0x800a82c3, zeros;
; his chat picks blocks 0-18 only). The array is copied to his stack each frame; nothing
; there is ever run. docs/re/bugs.md 2.3.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

; --- Guy ---
.org 0x800b62f8                 ; Talk, someone hasn't met Guy, block chosen by stage
    j       guy_reintro         ; was: lui v1, 0x8008
    nop                         ; was: j 0x800b7800 (its delay slot sets v0 = 0x23)

.org 0x800b6f48                 ; state 0x23: the introduction script
    j       guy_intro_run       ; was: lui v0, 0x8008
    nop                         ; was: lb v0, talk_block(v0)

; --- Fontana ---
.org 0x800d0e80                 ; Talk, not everyone unmet: was jal rand_upto (services)
    j       fontana_reintro     ; (delay slot: addiu a0, zero, 1, kept)

.org 0x800d1574                 ; state 0x23: the introduction script
    j       fontana_intro_run   ; was: lui v0, 0x8008
    nop                         ; was: lb v0, talk_block(v0)

.org 0x800a7e14
.area 0x800a82c4 - .
guy_reintro:                    ; count the members who haven't met Guy (met_bits[0] bit 0)
    lui     t0, 0x8008
    addiu   t0, t0, -0x17ee     ; party slots, 0x8007e812
    addiu   t2, t0, 6
    move    t3, zero
@@scan:
    lb      v1, 0(t0)
    addiu   t0, t0, 1
    bltz    v1, @@next
    sll     v0, v1, 1
    addu    v0, v0, v1
    sll     v0, v0, 2
    addu    v0, v0, v1
    sll     v0, v0, 4           ; * 0xd0
    lui     t1, 0x8008
    addu    v0, v0, t1
    lbu     v0, -0x28f8+0xc6(v0)
    nop
    andi    v0, v0, 1
    bnez    v0, @@next
    nop
    addiu   t3, t3, 1
@@next:
    bne     t0, t2, @@scan
    nop
    lui     v1, 0x8008
    lb      v0, -0x17ef(v1)     ; party count, 0x8007e811
    nop
    beq     t3, v0, @@go        ; nobody has met him: the introductions, as chosen
    addiu   v0, zero, 3
    sb      v0, -0x644c(v1)     ; some have: talk_block 3, the re-introduction
@@go:
    j       0x800b7800          ; talk_state = 0x23 (v1 = 0x80080000)
    addiu   v0, zero, 0x23

guy_intro_run:
    lui     v0, 0x8008
    lb      v0, -0x644c(v0)     ; talk_block
    addiu   v1, zero, 3
    bne     v0, v1, @@stack
    addiu   v1, sp, 0x3768      ; the introduction array
    la      a0, guy_reintro_script
    j       0x800b6fa8          ; jal talk_script_run (delay slot nop)
    nop
@@stack:
    sll     a0, v0, 1
    addu    a0, a0, v0
    sll     a0, a0, 3
    addu    a0, a0, v0
    sll     a0, a0, 3           ; * 200
    j       0x800b6fa8
    addu    a0, v1, a0

fontana_reintro:                ; fp = members who haven't met Fontana (fewer than all)
    sll     t0, fp, 24
    sra     t0, t0, 24
    blez    t0, @@services      ; everyone has: services and chat, as before
    lui     v0, 0x8008
    lw      v1, -0x69e8(v0)     ; npc_stage
    nop
    andi    t1, v1, 0x80
    bnez    t1, @@set
    addiu   t2, zero, 3         ; stage 1
    andi    t1, v1, 0x100
    bnez    t1, @@set
    addiu   t2, zero, 4         ; stage 2
    andi    t1, v1, 0x200
    bnez    t1, @@set
    addiu   t2, zero, 5         ; stage 3
    addiu   t2, zero, 3         ; (not reached: an unmet member is only counted at a stage)
@@set:
    sb      t2, -0x644c(v0)     ; talk_block
    j       0x800d0e74          ; talk_state = 0x23
    nop
@@services:
    jal     0x8001cb18          ; rand_upto(1), as the original
    addiu   a0, zero, 1
    j       0x800d0e88
    nop

fontana_intro_run:
    lui     v0, 0x8008
    lb      v0, -0x644c(v0)
    nop
    slti    v1, v0, 3
    bnez    v1, @@stack
    addiu   v1, sp, 0x568       ; the introduction array
    la      v1, fontana_reintro_scripts - 12
    sll     v0, v0, 2
    addu    v1, v1, v0
    lw      a0, 0(v1)
    j       0x800d15ac          ; jal talk_script_run; its delay slot adds v1
    move    v1, zero
@@stack:
    j       0x800d1598
    nop

fontana_reintro_scripts:
    .word   fontana_reintro_1, fontana_reintro_2, fontana_reintro_3

; Opcodes as in talk_script_run (0x800b8ccc): 7 bar, 6 load, 0 show, 3 face, 2 say, 1 hide,
; -1 end. Characters: 0 Guy, 1 Linaria, 2 Alstron, 3 Lychee; 9 Fontana, 10 Zaril,
; 11 Artemisia, 12 Lilia, 13 Cephala, 7 Reiran.
guy_reintro_script:
    .halfword 7,302
    .halfword 6,0, 0,0,109, 3,0,3,109, 2,134, 1,0,109        ; Guy: "Didn't I tell you already?"
    .halfword 6,2, 0,2,178, 3,2,0,178, 2,135                  ; Alstron
    .halfword 6,1, 0,1,8, 3,1,3,8, 2,136, 1,1,8               ; Linaria
    .halfword 6,3, 0,3,8, 3,3,0,8, 2,137, 3,3,1,8, 2,138, 3,3,5,8, 2,139  ; Lychee
    .halfword -1
fontana_reintro_1:
    .halfword 7,282
    .halfword 6,9, 0,9,109, 3,9,3,109, 2,117, 1,9,109         ; Fontana
    .halfword 6,10, 0,10,178, 3,10,0,178, 2,118, 1,10,178     ; Zaril
    .halfword 6,11, 0,11,8, 3,11,2,8, 2,119, 1,11,8           ; Artemisia
    .halfword 6,12, 0,12,178, 3,12,3,178, 2,120, 3,12,1,178, 2,121, 1,12,178  ; Lilia
    .halfword 6,13, 0,13,109, 3,13,1,109, 2,122               ; Cephala
    .halfword -1
fontana_reintro_2:
    .halfword 7,282
    .halfword 6,9, 0,9,109, 3,9,3,109, 2,117, 1,9,109
    .halfword 6,11, 0,11,8, 3,11,2,8, 2,119, 1,11,8
    .halfword 6,12, 0,12,178, 3,12,3,178, 2,120, 3,12,1,178, 2,121, 1,12,178
    .halfword 6,13, 0,13,109, 3,13,1,109, 2,122
    .halfword -1
fontana_reintro_3:
    .halfword 7,282
    .halfword 6,9, 0,9,109, 3,9,3,109, 2,117, 1,9,109
    .halfword 6,13, 0,13,109, 3,13,1,109, 2,122, 1,13,109
    .halfword 6,7, 0,7,109, 3,7,2,109, 2,123                  ; Reiran
    .halfword -1
.endarea
.close
