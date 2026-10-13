; Adventurer's Inn (JOUKA.BIN): center "Not enough gold." (SISETU 57).
;
; The Inn's message row (y 0xa6) centers its lines through 0x800dba48, which sets the
; centering flag (0x80079772) and calls text_at (0x800dbd7c) with no x. "Not enough
; gold." alone was printed by calling text_at straight, at a fixed x of 0x70: お金がたりま
; せん is eight 12 px glyphs, 112 to 208, centered by hand. The English line is 83 px,
; so it sat 9 px left of the row's other lines (start 112 against 121). Two places in
; the room code print it, with the same arguments (0x800c6cd8, 0x800c7054).
;
; Both now call 0x800dba48 like the Inn's other messages. It calls 0x800216a0 with 1,
; as both sites did themselves (a0 is 1 on every path in), sets the flag, which text_at
; clears again, and passes the same 4, string and last argument (1). The store into
; 0x8007993a stays before the call, as it was. s0 still ends up 1, which the code after
; it stores.
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000

.macro centered_gold, at
.org at
.area 0x30, 0
    lui     v0, 0x8008
    lhu     v1, -0x67ee(v0)
    lui     v0, 0x8008
    sh      v1, -0x66c6(v0)         ; as before (0x8007993a)
    addiu   a0, zero, 0xa6          ; y
    addiu   a1, zero, 4
    addiu   a2, zero, 0x39          ; SISETU 57, "Not enough gold."
    addiu   s0, zero, 1
    jal     0x800dba48              ; the centered printer
    move    a3, s0
.endarea
.endmacro

centered_gold 0x800c6cd8            ; was text_at(0x70, 0xa6, 4, 57) after 0x800216a0(1)
centered_gold 0x800c7054

.close
