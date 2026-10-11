; Game bug fix: a failed raise at the Temple keeps the party table in step.
;
; When a raise from ashes fails, temple_heal's Lost path deletes the character and calls
; roster_compact (0x800dcb70), which moves every higher record down a slot. Every other
; place that deletes a character then calls party_index_fixup (0x800dcdec) with the
; deleted index, which drops it from every party and lowers the higher indexes; the
; Temple didn't. Parties above the lost character then listed the wrong people, and a
; party left fallen in the maze could end up listing nobody who's actually there, so its
; bodies couldn't be found (docs/re/fallen-parties.md).
;
; The call now goes to a short routine that does both, with the Temple's character
; (0x80079888) as the index. It's placed over JOUKA 0x800a6c40, an unreferenced debug
; menu (it toggles debug_flags; no call, pointer or computed address reaches it).
; docs/re/bugs.md 1.9.
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000

.org 0x800cb030
    jal     temple_lost_compact ; was: jal roster_compact (delay slot unchanged)

.org 0x800a6c40
.area 0x40
temple_lost_compact:
    addiu   sp, sp, -8
    sw      ra, 4(sp)
    jal     0x800dcb70          ; roster_compact
    nop
    lui     a1, 0x8008
    lb      a0, -0x6778(a1)     ; the Temple's character
    jal     0x800dcdec          ; party_index_fixup(index)
    nop                         ; not lb here: its first instruction copies a0 (load delay)
    lw      ra, 4(sp)
    nop
    jr      ra
    addiu   sp, sp, 8
.endarea
.close
