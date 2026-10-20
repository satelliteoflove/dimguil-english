; Reopened content: Rosea's greetings for Balbo's party (NPC_MES2 52, 53, 56, 57).
;
; Rosea's picker (MCARD 0x800cd600) sets three flags over the party: a3, someone knows
; Loktofeit (+0x5a bit 1) or carries the Ruby Slippers (item 0x11e); t2, a man aged 16-25;
; and t1, a lost character waiting at the 0x80096720 list. It was built like Guy's party's
; picker (0x800be88c, Lychee's 1:72), which also checks each member's name against a list
; of rude words, but Rosea's name check was never written. Where it should be tested
; (0x800cd9ec), a0 is compared with s0, and both are always 1 (a0 is set in the delay slot
; at 0x800cd7a4). So without a3 every party that had no lost character got 2:56, "too
; embarrassing to say, {name}", with no name copied (so {ff12} was whatever the buffer
; last held), and 2:57 (a young man) and 2:52 / 2:53 (plain hello, a coin flip) never
; played. With a3, t1 and t2 together the greeting is a 1-in-4 pick of 54-57, and its 56
; had the same missing name.
;
; Now:
; - The name check is written: rosea_dirty compares each member's whole name, terminator
;   included, with Guy's list (twelve 10-byte entries at 0x800a1eb0, compare lengths at
;   0x800a1f28), so one list serves both. It compares unsigned bytes. (Guy's own loop
;   loads the list's bytes signed, lb, against the name's lbu, so any byte from 0x80 up,
;   the 0xff terminator included, never matches and Lychee's line can't show; that's
;   reported in docs/re/bugs.md, not fixed here.) It returns a0 = 1 and t5 = the first
;   matching member's record, or a0 = 0.
; - Without a3: a lost character gives 2:55 as before; a rude name gives 2:56 with that
;   member's name copied into 0x80089ac0 for {ff12}; a man aged 16-25 gives 2:57;
;   anyone else gets 2:52 or 2:53.
; - With a3, t1 and t2, the random pick's case 2 gives 2:56 with the name when there's a
;   rude name, and 2:54 (the line every other a3 party gets) when there isn't.
;
; Space: the random pick's case 1 (lost character, 2:55) had its own copy of the same
; 52-word "copy the lost name, 2:55" code that the no-a3 path has (0x800cd91c-0x800cd9e8).
; It now jumps to that one, and the new code sits in the 50 words freed (0x800cd7f4-
; 0x800cd8bb). No branch from outside that range lands in it. Chris approved the fix in
; outline (2026-10-19). docs/re/bugs.md 1.18.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800cd798                 ; after the three flag loops; was: move v1, a3 / addiu v0, zero, 1
    jal     rosea_dirty         ;   / bne v1, v0, 0x800cd914 / addiu a0, zero, 1 (a0: the flag)
    move    v1, a3
    beqz    v1, 0x800cd914      ; a3 is 0 or 1: the same test as bne v1, 1
    nop

.org 0x800cd7ec                 ; random pick 1: was the duplicate lost-name copy
    j       0x800cd91c          ; the no-a3 path's copy (its first instruction: move a2, zero)
    nop
.area 0x800cd8bc - .            ; the 50 freed words, 0x800cd7f4-0x800cd8bb

; v1, a3, t1 and t2 are kept; uses t3-t9, a0-a2, v0, hi/lo.
rosea_dirty:
    lui     t3, 0x8008
    addiu   t3, t3, -0x17ee     ; party slots, 0x8007e812
    addiu   v0, zero, 6
@@slot:
    lb      t4, 0(t3)           ; roster index, -1 = empty
    addiu   t6, zero, 0xd0
    bltz    t4, @@slot_end
    lui     t8, 0x800a
    mult    t4, t6
    addiu   t6, t8, 0x1f28      ; compare lengths
    addiu   t8, t8, 0x1eb0      ; the list
    mflo    t5
    lui     t7, 0x8008
    addu    t5, t5, t7
    addiu   t5, t5, -0x28f8     ; the record, 0x8007d708 + 0xd0 * index; the name is at +0
@@entry:
    lbu     t7, 0(t6)
    move    t9, t5
    move    a2, t8
@@byte:
    lbu     a0, 0(a2)
    lbu     a1, 0(t9)
    addiu   t7, t7, -1
    bne     a0, a1, @@next_entry
    addiu   a2, a2, 1
    bnez    t7, @@byte
    addiu   t9, t9, 1
    jr      ra
    addiu   a0, zero, 1         ; a match: t5 = its record
@@next_entry:
    addiu   t6, t6, 1
    andi    a0, t6, 0xffff
    xori    a0, a0, 0x1f34      ; past the twelfth length
    bnez    a0, @@entry
    addiu   t8, t8, 10
@@slot_end:
    addiu   v0, v0, -1
    bnez    v0, @@slot
    addiu   t3, t3, 1
    jr      ra
    move    a0, zero

; 2:56 with the name: t5 = the matching member's record.
rosea_copy:
    lui     t6, 0x8009
    addiu   t6, t6, -0x6540     ; 0x80089ac0, the {ff12} name
    addiu   t7, t5, 10
@@copy:
    lbu     t8, 0(t5)
    addiu   t5, t5, 1
    sb      t8, 0(t6)
    bne     t5, t7, @@copy
    addiu   t6, t6, 1
    lui     v1, 0x8008
    addiu   v0, zero, 3
    sb      v0, -0x6913(v1)     ; expression 3, as before
    j       0x800cda4c          ; sh v0, talk_str_a
    addiu   v0, zero, 0x38
.endarea

.org 0x800cd8c4                 ; random pick 2: was ed 3 / 2:56 with no name
    jal     rosea_dirty
    nop
    bnez    a0, rosea_copy
    nop
    j       0x800cd900          ; no rude name: 2:54, expression 0 (delay slot: the next
                                ; block's addiu v0, zero, 3, harmless)

.org 0x800cda00                 ; no a3: 2:56, now only for a rude name; was j 0x800cda4c
    j       rosea_copy

.close
