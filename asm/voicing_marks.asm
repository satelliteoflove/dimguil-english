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
; - Two more printers merge inline, like the event box, without the helper: BATTLE's
;   (0x800d19a4, the battle box and battle menus) and MAZE's text_draw (0x800a201c).
;   "Ocelotl tries to blow away" printed "b  away": "lo" + "w " drew a blank kana cell
;   (FIGHTMSG 33 in message 109, found by the T5 screen checks, 2026-10-13).
;
; None of them merge now: each inline "is the next glyph a mark" test always says no (the
; event printer still reads the next byte, which the rest of the routine uses), and every
; copy of the helper returns 0. Two-byte voiced kana (0xf7 xx) take a different path.
;
; The line measures skipped the marks too, since a merged mark takes no room. A line with
; `"` or "w " was measured short and centered right of center, half the glyph's width per
; mark (2 px per `"`, 6 px per "w "): 81 event lines, "Learned new spells." at the Inn,
; and battle lines with "w " ("tries to blow away"). Every measure counts them now: the
; event box (first line 0x8001fb4c, later lines 0x8001ff04, large font only), the battle
; box (0x80022024, large font only), text_at in MAZE, MCARD, JOUKA and HAZURE (always),
; and the wrap column the expander keeps for an inserted name (0x8001dfc0, large font
; only), so a name with "w " can't run a battle line one code past 24.
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800
.org 0x8001ffe8
    move    v0, zero            ; was sltiu v0, v0, 2 (next glyph - 0xb6 < 2)

; Measures: "is this glyph a mark" always says no, so every glyph is counted.
.org 0x8001e2d0                 ; expander, name copy: wrap column
    move    v0, zero            ; was sltiu v0, v0, 2 (glyph - 0xb6 < 2)
.org 0x8001fc98                 ; event box, first line
    move    v0, zero            ; was sltiu v0, v0, 2
.org 0x800201f0                 ; event box, later lines
    move    v0, zero            ; was sltiu v0, v0, 2
.org 0x800220cc                 ; battle box line
    move    v0, zero            ; was sltiu v0, v0, 2
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

; One instruction in an overlay: "is it a mark" (sltiu v0, v0, 2) always says no.
.macro not_a_mark, file, at
    .open file, 0x800a1000
    .org at
        move    v0, zero        ; was sltiu v0, v0, 2 (glyph - 0xb6 < 2)
    .close
.endmacro

; Inline merges
not_a_mark "dirty/dimguil/BATTLE.BIN", 0x800d1a68
not_a_mark "dirty/dimguil/MAZE.BIN", 0x800a20e0

; text_at's centering measure
not_a_mark "dirty/dimguil/MAZE.BIN", 0x800a1f7c
not_a_mark "dirty/dimguil/MCARD.BIN", 0x800ad618
not_a_mark "dirty/dimguil/JOUKA.BIN", 0x800dbe2c
not_a_mark "dirty/dimguil/HAZURE.BIN", 0x800bca4c
