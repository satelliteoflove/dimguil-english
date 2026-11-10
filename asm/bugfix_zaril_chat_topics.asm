; Zaril's chat: replies that don't fit the topic (NPC_MES5 74-97, docs/re/bugs.md 2.10).
;
; Each chat block of Zaril's party (talk handler 4, the array the handler copies to
; sp+0x3d8) is one script: the bottom-bar topic line ('bar' op 7), then Zaril,
; Fritillaria and Gaura, each reply after a 'face' op (op 3: slot, expression, position)
; that sets the portrait's expression. In the original, several blocks show a topic line
; their replies don't answer. Chris went through the table block by block (2026-11-09,
; docs/work/zaril-chat-compare.html) and approved these changes. Every line stays with
; its speaker, and a moved line takes its own expression along. Blocks 0-5, 7 and 12
; don't change.
;
;   block 6:  topic "told them" (99) -> "new information" (98)
;   block 8:  topic "something personal" (102) -> "told them" (99); Gaura's 82 ("I'm
;             slow, but the rest, great") -> his block-1 "Mmm..." (59)
;   block 9:  topic "told them" (99) -> "new information" (98); Fritillaria's 84 (how
;             Zaril saved him, grin) <-> his 87 ("nothing new to spill, sorry", sorry
;             look) from block 10
;   block 10: Fritillaria's 87 -> 84, with the grin
;   block 11: Gaura's 91 ("Samurai, someday", the same Japanese as 88 in block 10) -> 82
;   block 13: topic "new information" (98) -> "told them" (99); Zaril's 95 ("Sorry.
;             Nothing new to tell", the same Japanese as 83 in block 9) -> his 80
;             ("greenhorns too"), with its expression (0)
;
; The table is plain data in MCARD at 0x800a8988, 200 bytes a block, in halfwords; only
; operands change. Original values are in the comments.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800a8e3a                 ; block 6 bar: 99
    .halfword 98

.org 0x800a8fca                 ; block 8 bar: 102
    .halfword 99
.org 0x800a9018                 ; block 8 Gaura say: 82 (face 0, unchanged)
    .halfword 59

.org 0x800a9092                 ; block 9 bar: 99
    .halfword 98
.org 0x800a90be                 ; block 9 Fritillaria face expression: 1
    .halfword 3
.org 0x800a90c4                 ; block 9 Fritillaria say: 84
    .halfword 87

.org 0x800a9186                 ; block 10 Fritillaria face expression: 3
    .halfword 1
.org 0x800a918c                 ; block 10 Fritillaria say: 87
    .halfword 84

.org 0x800a9270                 ; block 11 Gaura say: 91 (face 0, unchanged)
    .halfword 82

.org 0x800a93b2                 ; block 13 bar: 98
    .halfword 99
.org 0x800a93c2                 ; block 13 Zaril face expression: 3
    .halfword 0
.org 0x800a93c8                 ; block 13 Zaril say: 95
    .halfword 80
.close
