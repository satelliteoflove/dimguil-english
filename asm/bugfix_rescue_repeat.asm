; Game bug fix: an NPC rescue frees the rescued party's record, so the same party isn't
; offered (and charged) again.
;
; Guy's, Balbo's and Fontana's handlers (talk_guy 0x800b5694, talk_balbo 0x800c7264,
; talk_fontana 0x800cf8c0) offer a rescue for any party in the table, other than the
; current one, whose members all have status above 0x1f. They don't look at where the
; members are. On Yes they set each member's area to 0xff and take the fee, but leave
; the party's record in place, so the bodies, now at the Temple, are still a candidate:
; the offer came back in the same meeting and at later ones, and each Yes took the fee
; again (Fontana: half the gold and the first, third, fifth... items, every time). The
; record only went when the town's cleanup ran, after a wipe, a load or "Go On with
; Another Party". docs/re/rescue-test.md has the test.
;
; Now each Yes ends by freeing the picked party's record as Look for Companions does for a
; party it empties: id -1, count 0, members -1, member_state 0xff. Nothing else changes:
; the fee and the move to town are the original code's. No MCARD routine frees a party
; record (Look for Companions and the town's cleanup do it inline; BATTLE's
; party_record_clear only clears the current party and isn't loaded during a talk), so
; the three hooks share one small routine here.
;
; Hooks, each at the Yes branch's exit after the member loop:
;   Guy    0x800b7f44  j 0x800b7f60 (delay slot: addiu v1, zero, 0x43, kept)
;   Balbo  0x800cad6c  j 0x800cad84 (delay slot: lui v0, 0x8008, kept)
;   Fontana 0x800d24e4 lui v1, 0x8008 / lb v0, roster_count(v1) (moved into the stub)
; The handlers save ra in their prologues and call rand_upto in this same branch, so ra
; and the t registers are free here.
;
; Space: two unreferenced routines in MCARD at 0x800ab1cc-0x800ab27b (each just calls
; 0x800255b0 four times; no jal, j, branch or pointer reaches them from any module), after
; the Zaril scripts in bugfix_zaril_heal.asm.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800b7f44                 ; Guy, Yes: was j 0x800b7f60
    j       guy_rescued

.org 0x800cad6c                 ; Balbo, Yes: was j 0x800cad84
    j       balbo_rescued

.org 0x800d24e4                 ; Fontana, Yes: was lui v1, 0x8008 / lb v0, -0x676f(v1)
    j       fontana_rescued
    nop

.org 0x800ab1cc
.area 0x800ab27c - .
; Frees parties[rescue_candidates[rescue_candidate_count]], the party the Yes just
; carried back (the handlers store their rand_upto pick in rescue_candidate_count).
; Uses t5-t8; returns by ra.
rescue_free_party:
    lui     t5, 0x8008
    lb      t5, -0x676b(t5)     ; rescue_candidate_count (0x80079895): the pick
    lui     t6, 0x8009
    addu    t6, t6, t5
    lb      t6, -0x2d00(t6)     ; rescue_candidates[pick] (0x8008d300): the party slot
    lui     t5, 0x8009
    sll     t7, t6, 3
    subu    t7, t7, t6          ; x7
    sll     t7, t7, 2           ; x28
    subu    t7, t7, t6          ; x27
    sll     t7, t7, 1           ; x54 = 0x36, one party record
    addu    t7, t7, t5
    addiu   t7, t7, -0x738      ; &parties[slot] (0x8008f8c8)
    addiu   t8, zero, -1
    sb      t8, 0(t7)           ; id = -1
    sb      zero, 1(t7)         ; count = 0
    addiu   t6, zero, 6
@@member:
    sb      t8, 2(t7)           ; members[k] = -1
    sb      t8, 0xe(t7)         ; member_state[k] = 0xff
    addiu   t6, t6, -1
    bnez    t6, @@member
    addiu   t7, t7, 1
    jr      ra
    nop

guy_rescued:                    ; v1 = 0x43 from the hook's delay slot
    jal     rescue_free_party
    nop
    lui     v0, 0x8008
    j       0x800b7f60          ; talk_state = 0x43 (needs v0 = 0x80080000, v1 = 0x43)
    addiu   v1, zero, 0x43

balbo_rescued:
    jal     rescue_free_party
    nop
    j       0x800cad84          ; talk_state = 0x43 (needs v0 = 0x80080000)
    lui     v0, 0x8008

fontana_rescued:
    jal     rescue_free_party
    nop
    lui     v1, 0x8008
    j       0x800d24ec          ; on to the pack compaction loop
    lb      v0, -0x676f(v1)     ; roster_count
.endarea
.close
