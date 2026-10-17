; Center "{name} can't act." (SISETU 525) for the English font.
;
; Choosing a member who is paralyzed, stoned, dead, ashes or lost (status & 0x3e0) at the
; locked-door picker prints 525 in the message bar from FUN_800ae1c8's state 2. The
; routine counts the name (0x800ae3f8-0x800ae47c: s2 = the index of the 0x40 in the
; name's 0xff 0x40 terminator, so name length + 1) and places the line at
; x = (320 - 12 x (s2 + 10)) / 2 (0x800ae480-0x800ae498), sized for the Japanese
; {name}は,行動できません。 in 12 px glyphs. The English font is proportional: a name
; letter is 4-8 px (lowercase about 5, a capital 7-8), " can't act." is 49 px. So the
; English sat well left of center ("Kai can't act." about 50 px left).
;
; Now x = 136 - (5 x s2) / 2: the line taken as 5 px a letter plus a capital, plus the
; 49, centered on 160 like the original. Within 2.5 px of center for mixed-case names of
; 1 to 8 letters (all capitals run up to about 6 px right). The first instruction is the
; loop branch's delay slot, as before, and still writes only v1, which the loop reloads.
; Chris approved it on 2026-10-17 (docs/re/lock-test.md problem 4).
.psx
.open "dirty/dimguil/MAZE.BIN", 0x800a1000

.org 0x800ae480
    sll     v1, s2, 2           ; was: addiu v1, s2, 10
    addu    v1, v1, s2          ; was: sll v0, v1, 1     v1 = 5 x s2
    sra     v1, v1, 1           ; was: addu v0, v0, v1
    addiu   a0, zero, 136       ; was: sll v0, v0, 2
    subu    a0, a0, v1          ; was: addiu a0, zero, 0x140
    nop                         ; was: subu a0, a0, v0
    nop                         ; was: sra a0, a0, 1

.close
