; No Japanese voicing marks in English text.
;
; Glyphs 0xb6 and 0xb7 are the Japanese voicing marks (゛ and ゜). In the English font
; 0xb6 is `"` and 0xb7 is the digraph "w ". The printers look one glyph ahead, and when
; the next one is 0xb6 or 0xb7 they draw the current glyph as its voiced form from the
; kana sheet and swallow the mark. English never wants that.
;
; - The maze's event box (switches, doors, story text) prints through 0x8001ff04, which
;   merges with no check on the first glyph at all: "how hard" printed as "ズhard" (ho +
;   "w ") and `satisfying "click."` lost its g and both quote marks (event 288; Chris
;   caught it in play). 91 event strings had a merge somewhere.
; - The other printers ask a helper (glyph, next glyph) that merges only after codes that
;   are kana with a voiced form. Each overlay has its own copy: MAZE, MCARD (loaded for NPC
;   talks), JOUKA (town), CMENU, HAZURE and BATTLE. That's why a quote inside a line was
;   only sometimes wrong (`y "` printed as ブ), and why Guy's "Well, I blew it." printed
;   "le" + "w " as a Japanese glyph (NPC_MES1 94).
;
; None of them merge now: the event printer's "is the next glyph a mark" test always says
; no (it still reads the next byte, which the rest of the routine uses), and every copy of
; the helper returns 0. Two-byte voiced kana (0xf7 xx) take a different path.
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800
.org 0x8001ffe8
    move    v0, zero            ; was sltiu v0, v0, 2 (next glyph - 0xb6 < 2)
.close

.macro no_voicing, file, at
    .open file, 0x800a1000
    .org at
        jr      ra              ; no voicing mark, whatever the glyphs
        move    v0, zero
    .close
.endmacro

no_voicing "dirty/dimguil/MAZE.BIN", 0x800a3134
no_voicing "dirty/dimguil/MCARD.BIN", 0x800ae4e4
no_voicing "dirty/dimguil/JOUKA.BIN", 0x800dc76c
no_voicing "dirty/dimguil/CMENU.BIN", 0x800be944
no_voicing "dirty/dimguil/HAZURE.BIN", 0x800bd2f8
no_voicing "dirty/dimguil/BATTLE.BIN", 0x800d3510
