; The Inn's room list: room for the whole help line.
;
; Each town screen sets up its four text layers through 0x800db3d0 (sizes for layers
; 0-3, out of a 720-sprite pool). Layer 1 holds the facility name, the menus and the
; one-line help bar. The Inn doesn't set up layers of its own: it keeps the town map's
; (186, 154, 186, 114), as do the King's Chambers and Edge of Town. In the room list
; (seven lines padded with spaces to line up the prices) layer 1 was full at 154, and
; the room help lines lost their ends ("Restores all HP for 10000G a").
;
; The town map now asks for 172: the room list is 133 sprites without its help line,
; and the help bar shows about 39 glyphs. Measured over every town screen, nothing else
; on those screens comes near 154 (the King's fullest page with its title and caption
; is 129). Every other screen keeps the sizes it asked for; the pool has 80 to spare on
; most of them, so the extra 18 are free.
.psx

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800a348c
    addiu   a1, zero, 172       ; was 154 (0x9a)
.close
