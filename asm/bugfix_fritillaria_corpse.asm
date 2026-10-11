; Game bug fix: Fritillaria names the right "walkin' corpse" (NPC_MES5 17).
;
; greet_fritillaria_line (0x800dba44) greets the party with 5:16 ("the murder squad") if
; a member has 10,000+ kills, and 5:17 ("Hey! It's {ff12}, the walkin' corpse!") if one
; has died 10+ times, a coin flip deciding when both are true. Two slips:
;   - The loops that find whose name goes in 5:17 tested kills (lw +0xc0, < 10000), not
;     deaths (lbu +0xc4, < 10). With nobody at 10,000 kills they ran off the end of the
;     party and named whoever 0x8007e818 points at (roster character 0, as a rule).
;   - On heads, the both-true case set 5:17 and copied the name, then fell into the
;     kills-only branch, which set 5:16 again. On tails it jumped there to do the same.
; Both loops now test deaths. Tails goes straight to the end with 5:16; heads goes on
; into the deaths-only branch (the bne at 0x800dbc3c takes it when v0 isn't 1), which
; sets 5:17 and the name. docs/re/bugs.md 1.6.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
.org 0x800dbb34
    j       0x800dbdbc          ; tails, 5:16 already set (was j 0x800dbc38)
.org 0x800dbb98
    lbu     v0, 0xc4(v0)        ; deaths (was lw v0, 0xc0(v0), kills)
.org 0x800dbba0
    sltiu   v0, v0, 10          ; was 0x2710
.org 0x800dbc38
    addiu   v0, zero, 2         ; heads: on to the 5:17 branch (was 1)
.org 0x800dbcc4
    lbu     v0, 0xc4(v0)        ; deaths
.org 0x800dbccc
    sltiu   v0, v0, 10          ; was 0x2710
.close
