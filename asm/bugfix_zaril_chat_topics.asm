; Zaril's chat: replies that don't fit the topic (NPC_MES5 74-97, docs/re/bugs.md 2.10).
;
; Each chat block of Zaril's party (talk handler 4, the array the handler copies to
; sp+0x3d8) is one script: the bottom-bar topic line ('bar' op 7), then Zaril,
; Fritillaria and Gaura, each reply after a 'face' op (op 3: slot, expression, position)
; that sets the portrait's expression. In the original, a few blocks show a topic line
; their replies don't answer. Zaril's and Gaura's replies are copies of their lines in
; Fontana's and Balbo's chat tables (NPC_MES3, NPC_MES2), which show the topic the
; writers gave each line; Fritillaria's are new to this table. Approved by Chris
; (2026-11-09, narrowed 2026-11-10, docs/work/zaril-chat-compare.html). Every line stays
; with its speaker, and a moved line takes its own expression along. Blocks 0-5, 7, 8,
; 11 and 12 don't change.
;
;   block 6:  topic "told them" (99) -> "new information" (98); all three replies are
;             no-news replies (Zaril's and Gaura's come from "new information" blocks)
;   block 9:  topic "told them" (99) -> "new information" (98), the same evidence;
;             Fritillaria's 84 (how Zaril saved him, grin) <-> his 87 ("nothing new to
;             spill, sorry", sorry look) from block 10
;   block 10: Fritillaria's 87 -> 84, with the grin
;   block 13: topic "new information" (98) -> "told them" (99); Gaura's 97 ("I heard it
;             already") comes from a "told them" block, and Fritillaria's 96 ("Aw, that
;             again") goes with it
;
; The table is plain data in MCARD at 0x800a8988, 200 bytes a block, in halfwords; only
; operands change. Original values are in the comments.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800a8e3a                 ; block 6 bar: 99
    .halfword 98

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

.org 0x800a93b2                 ; block 13 bar: 98
    .halfword 99
.close
