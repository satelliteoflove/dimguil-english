; Boltac's catalog: start item descriptions 9 px higher under the tall pictures.
;
; The catalog draws an item's picture, then its description below it, and clips the
; text at the bottom of the parchment (y=227) with no scrolling. Under the 55 tall
; (152x152) pictures the description starts 39 px lower than under the normal ones,
; which left room for 4 lines. Here the offset is 30, and the tall pictures are cut to
; 143 rows (scripts/itempics.py), so 5 lines fit. Normal items are unchanged.
;
; s3 is 1 for an item with a tall picture, else 0. The original built s3 * 39 as
; ((s3 << 2) + s3) << 3 - s3; this masks a constant instead.
.psx

.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800deb1c             ; was: sll v0,s3,2 / addu v0,v0,s3 / sll v0,v0,3 / subu v0,v0,s3
    subu    v0, zero, s3    ; 0 or -1
    andi    v0, v0, 30      ; tall offset in px (was 39)
    nop
    nop
.close
