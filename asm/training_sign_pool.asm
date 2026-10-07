; The training maze's sign: room for the English text.
;
; Searching at the sign in the training maze shows SISETU 492 in a large box. The maze
; code that opens it (0x800bef6c) resizes glyph layer 0 to exactly 172 sprites, one more
; than the Japanese text's 171 glyphs, so the English (207 glyph codes before it was
; reworded) stopped at "but as a b".
;
; The resize frees layer 0 and reallocates it first-fit; the maze otherwise keeps layer
; 0 at 192 sprites at the start of the pool, with layer 1 right after it, so 192 is the
; most this box can have without moving other layers. Here it gets 177, exactly what
; the reworded English takes, which leaves the rest of the 192 free. signfit.py checks
; the built string against the size set here.
.psx
.open "dirty/dimguil/MAZE.BIN", 0x800a1000
.org 0x800bef6c
    addiu   a0, zero, 177       ; was 172
.close
