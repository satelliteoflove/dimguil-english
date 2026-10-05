; Boltac's Trade screens: room for the whole caption.
;
; Text is drawn as one sprite per glyph, from pools ("layers") the screen sets up when it
; opens (0x800db3d0 -> 0x8001f150; 720 sprites in all). On the Trade screens layer 1
; holds both the shop name at the top and the one-line caption at the bottom, and it was
; 28 sprites: "Boltac's Trading Post" takes 14, so a caption showed only its first 14
; glyph codes ("Choose an item to un", "Which weapon i"). The Japanese name is 7
; glyphs, which left the Japanese captions room.
;
; Here layer 1 gets 58 and layer 0 gives up 30 (270 -> 240). Measured over every Trade
; flow, layer 0 never went above 130. The three calls below are the only ones that set
; up the Trade layout.
.psx

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800bb0a0
    li      a0, 240         ; layer 0, was 270
    li      a1, 58          ; layer 1, was 28
.org 0x800bbca4
    li      a0, 240
    li      a1, 58
.org 0x800c0d78
    li      a0, 240
    li      a1, 58
.close
