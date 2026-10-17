; Game bug fix: the party's Bacortu in a fixed battle seals the row it was aimed at, not
; group 1 or 2.
;
; Bacortu is a one-group spell (spell_flags_table 0x800d5874, spell 14 = 0x8441, bit 0x40),
; like Montino, Morlis and Madalto. In a fixed battle (0x80079bde = 1: story fights and the
; type-2 roaming parties) the group pick (0x800cf0dc) doesn't pick a group for these: it
; calls the row picker 0x800cf258 with row mode on (party_commands state 0x34, spells, or
; 0x54, items, with flag 0x40), which returns 1 for the front row and 2 for the back, and
; party_commands stores that as the member's target (combatant +0xb). cast_spell
; (0x800abcc0) loads it into target_group (0x800796ac). Every other group spell's handler
; then calls spell_group_range (0x800c999c), which turns the row into its first group
; (target_group) and returns its last, and loops over them (spell_madalto 0x800c9e7c,
; spell_montino 0x800adbc4, spell_morlis 0x800acb94). spell_bacortu (0x800c9e2c) has no
; such step: it adds the caster's level to battle_groups[target_group].seal (0x8008c486 +
; group * 8), so the row number was used as a group number and the cast sealed group 1 or
; group 2, whatever was aimed at.
;
; Now spell 14's entry in spell_handlers (0x800d838c + 14 * 4, was 0x800c9e2c) points at
; the routine below. In a fixed battle, with the party (or its summons, group 7) casting at
; a monster group, it does what spell_madalto does: spell_group_range, then the original
; spell_bacortu once for each group of the row, each with the full caster level, no
; resistance check (as before). Everything else calls the original spell_bacortu once, as
; before: every ordinary battle, a monster's cast at the party (target 0) or at the
; summons (7), and a cast that Banoka turned back on its caster's own group. The caster
; test is the one thing Madalto's checks don't have: a monster's bounced spell targets its
; own group (cast_spell sets target_group = actor_group), a real group number, not a row.
; spell_bacortu itself is unchanged.
;
; Space: the dead FUN_800c3188 (nothing in BATTLE or MAIN reaches it), after the 7-word
; spell_sound_stop that bugfix_spell_sound_reload.asm put at its start. Chris approved
; the fix on 2026-10-17 (docs/re/decisions.md 30, bugs.md 1.16).
.psx
.open "dirty/dimguil/BATTLE.BIN", 0x800a1000

.org 0x800d838c + 14 * 4        ; spell_handlers[14], was .word 0x800c9e2c
    .word   spell_bacortu_rows

.org 0x800c31a4
.area 0x800c3300 - .            ; vwf.asm uses 0x800c3300-0x800c3307
spell_bacortu_rows:
    addiu   sp, sp, -0x20
    sw      ra, 0x18(sp)
    sw      s1, 0x14(sp)
    sw      s0, 0x10(sp)
    lui     s0, 0x8008
    lb      v1, -0x6422(s0)         ; 0x80079bde: 1 in a fixed battle
    lb      a0, -0x6866(s0)         ; actor_group (0x8007979a)
    addiu   v0, zero, 1
    bne     v1, v0, @@one
    move    v1, a0
    beqz    v1, @@party             ; the party casting
    addiu   v0, zero, 7
    bne     v1, v0, @@one           ; a monster: target_group is a group
@@party:
    lb      v1, -0x6954(s0)         ; target_group
    nop
    beqz    v1, @@one               ; the party (a bounce)
    addiu   v0, zero, 7
    beq     v1, v0, @@one           ; the summons
    nop
    jal     0x800c999c              ; spell_group_range: target_group = the row's first
    nop                             ; group, v0 = its last
    lb      v1, -0x6954(s0)
    move    s1, v0
    slt     v1, s1, v1
    bnez    v1, @@done              ; an empty row
    nop
@@row:
    jal     0x800c9e2c              ; spell_bacortu: seal target_group
    nop
    lbu     v0, -0x6954(s0)
    nop
    addiu   v0, v0, 1
    sb      v0, -0x6954(s0)         ; next group, as spell_madalto steps it
    sll     v0, v0, 24
    sra     v0, v0, 24
    slt     v0, s1, v0
    beqz    v0, @@row
    nop
    b       @@done
    nop
@@one:
    jal     0x800c9e2c              ; spell_bacortu, as before
    nop
@@done:
    lw      ra, 0x18(sp)
    lw      s1, 0x14(sp)
    lw      s0, 0x10(sp)
    jr      ra
    addiu   sp, sp, 0x20
.endarea

.close
