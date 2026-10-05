; Event text in the maze: room for English in the 3-line box.
;
; Text is drawn as one sprite per glyph, from pools ("layers"; see shop_caption_layer.asm).
; The maze opens its event box through 0x80021af0 (x, y, rows, columns, ...), which
; sizes layer 1 at rows x columns: 3 x 24 = 72 sprites, one per Japanese character. An
; English line of the same 288 px takes up to about 35 glyph codes, so long event text
; stopped dead once the three lines on screen held 72 (".........Sure enough, the" at
; the Shrine door; 48 strings were affected). The box scrolls, and a scrolled-off line
; gives its sprites back, so what counts is the three lines in view.
;
; Here the size is doubled to 144. The maze reserves 400 for layer 1 before it opens
; the box (layer 2 starts at 422), so nothing else gives anything up. The columns stay
; 24: they also set the box's centering width (24 x 12 = 288 px). Only the maze calls
; 0x80021af0 (twice, both 3 x 24). evfit.py checks every event string against 144.
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800
.org 0x80021bfc
    sll     a0, t2, 17          ; was 16: the size is (rows x columns) x 2
.close
