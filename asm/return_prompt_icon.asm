; The maze's "Press [triangle] to return to the Fortress City" prompt (SISETU 442).
;
; The triangle is a separate sprite (0x80015ce4) placed at a fixed x of -6 from screen
; centre, where the Japanese line has its space after 城塞都市に戻るには, (ten 12 px glyphs
; from the text's start at x 32). In the English the gap fell elsewhere, so the icon sat on
; "return". The English is now "Press [4 spaces] to return to the Fortress City."
; Measured in the emulator (350 px frame, picture from x 14): "Press" ends at frame x 71
; and "to" starts at 89; the triangle's visible ink is 6 px wide, starting 5 px right of
; the sprite's x + 155. -94 centres it in the gap.
;
; The line also has to fit the bar's glyph layer, 32 sprites (0x8001d07c sizes it for
; every bottom-bar message in the maze); the old wording took 33 and lost its period.
; This one takes 27.
.psx
.open "dirty/dimguil/MAZE.BIN", 0x800a1000
.org 0x800bab9c
    addiu   a1, zero, -94       ; icon x, was -6
.close
