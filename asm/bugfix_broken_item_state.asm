; Game bug fix: the town's BROKEN ITEM purge clears the emptied slot's state.
;
; On entering town, broken_items_purge (0x800db4c4) empties every pack slot holding
; item 0 (BROKEN ITEM), for every character, then zeroed item_state[9] (the tenth slot's
; uses left) instead of the emptied slot's own byte. A potion or scroll in the tenth slot
; lost its uses. The camp's copy (MAZE 0x800e6260) clears the right byte.
;
; The loop's tail is laid out again in place to clear 0x34 + slot. The counter is a small
; positive number, so the sign extension before its compare can go, which makes room.
; a2 = the character's record, a1 = slot, v1 = record + 2 * slot, t0 = -1.
; docs/re/bugs.md 1.10.
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800db510
.area 0x800db540 - .
    bne     v0, zero, @@next
    addiu   v0, a1, 1
    sh      t0, 0x20(v1)        ; items[slot] = empty
    addu    v1, a2, a1
    sb      zero, 0x34(v1)      ; item_state[slot] = 0 (was item_state[9])
@@next:
    move    a1, v0
    slti    v0, v0, 10
    bne     v0, zero, 0x800db4f8
    sll     v0, a1, 0x18
    jr      ra
    nop
    nop
.endarea
.close
