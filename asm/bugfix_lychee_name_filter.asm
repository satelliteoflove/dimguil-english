; Reopened content: Lychee's naughty-name line (NPC_MES1 72), "What's Lychee s'posed to
; call you? It's too embarrassing to say out loud! {name}... eek!"
;
; Guy's party's picker (MCARD 0x800be88c) compares each member's name with the
; naughty-name list (asm/naughty_names.asm). Two bugs kept the line from ever working:
; 1. The loop loads the name with lbu and the list with lb (0x800becfc), so the 0xff that
;    ends every entry is -1 on one side and 255 on the other, and nothing matches. Now lbu.
; 2. The line copies no name, so {ff12} showed whatever the buffer last held. The loop now
;    keeps each member's record offset (t2) in a spare stack byte pair (sp+0x16; local_a8
;    is 8 bytes and only 0x10-0x14 are used) and stops at the first match, so it holds the
;    matching member's. Stopping early changes nothing else: the rest of that loop only
;    tests class_sex & 0x80 == 3, which is never true. Where 1:72 is picked (the 1-in-4
;    roll and the plain branch) the name is copied into 0x80089ac0 on the way out, so only
;    when the line plays. The buffer is shared, as in the original: if Guy's own line in
;    the same greeting is 1:114 ("if it isn't {name}"), it shows the same name.
;
; Lychee's 'Mule' check (1:68, the lb at 0x800bebc8) is left as it was: Chris's decision
; on the tavern checks is still open (docs/re/bugs.md 2.9).
;
; Space: the copy sits over MCARD 0x800ab384-0x800ab3af, an unreferenced 11-word routine
; that renames a memory card save from SLPS_01146 (no jal, j, pointer or address load
; reaches it). Chris approved the fix (2026-10-19). docs/re/bugs.md 2.9.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800becfc                 ; the list byte, was: lb v0, 0x20(v0)
    lbu     v0, 0x20(v0)
    sh      t2, 0x16(sp)        ; was nop (load delay): this member's record offset
.org 0x800bed4c                 ; a match: was j 0x800bed6c (next member); delay sb t5, 0x14(sp) kept
    j       0x800bed88          ; done: sp+0x16 is the matching member's

.org 0x800bf048                 ; 1-in-4 roll, case 3: 1:72 (delay: sh v0, talk_str_a)
    j       lychee_copy
.org 0x800bf108                 ; the plain branch: 1:72 (delay: sh v0, talk_str_a)
    j       lychee_copy

.org 0x800ab384
.area 0x800ab3b0 - .
lychee_copy:                    ; the matching member's 10-byte name to 0x80089ac0
    lhu     t0, 0x16(sp)
    lui     t1, 0x8008
    addu    t0, t0, t1          ; records are 0xd0 apart from 0x8007d708: word aligned
    lw      t1, -0x28f8(t0)
    lw      t2, -0x28f4(t0)
    lhu     t3, -0x28f0(t0)
    lui     t4, 0x8009
    sw      t1, -0x6540(t4)
    sw      t2, -0x653c(t4)
    j       0x800bf15c          ; the picker's return
    sh      t3, -0x6538(t4)
.endarea

.close
