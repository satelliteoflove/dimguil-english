; Reopened content: Cresson greets a party as "boys", "girls" or "my good fellows"
; (NPC_MES4 18-20), by who is in it.
;
; greet_cresson_line (MCARD 0x800d8c98) picks Cresson's greeting line. After its special
; cases (a member named DIMGUIL, max HP over 9,999, everyone level 100 or more) it goes:
; s0 clear: 4:18 "Well, boys"; else s1 clear: 4:19 "Well, girls"; else t6 clear: 4:20
; "Well, my good fellows"; else 4:21 or nothing, by the Decipher table. s0, s1 and t6 are
; zeroed at the top and never set, so every party was "boys". Chris approved writing the
; check (2026-10-11).
;
; The smallest change that gives the rule: in the member loop, set s0 for a woman and s1
; for a man (class_sex +0x0b bit 7 is female: character creation sets it for a female,
; and a Valkyrie needs it). No women: s0 clear, "boys". Only women: s0 set, s1 clear,
; "girls". Mixed: both set, t6 clear, "my good fellows". t6 stays unset, as it always was;
; what the developers meant it for isn't recoverable from the code (bugs.md 2.4).
;
; Hook: the loop's level load (0x800d8dbc); the code sits in the never-run end of
; Cresson's chat array, after bugfix_reintroductions.asm. docs/re/bugs.md 2.4.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800d8dbc                 ; member loop, v1 = the member's record
    j       cresson_sex         ; was: lh v0, 0x44(v1) (level; next: nop)

.org 0x800a8280
.area 0x800a82c4 - .
cresson_sex:
    lbu     v0, 0x0b(v1)        ; class_sex
    nop
    andi    v0, v0, 0x80        ; bit 7: female
    beqz    v0, @@man
    nop
    j       @@level
    addiu   s0, zero, 1         ; a woman in the party
@@man:
    addiu   s1, zero, 1         ; a man in the party
@@level:
    j       0x800d8dc0          ; on to the level test, as before
    lh      v0, 0x44(v1)        ; the replaced load (0x800d8dc0 is a nop)
.endarea
.close
