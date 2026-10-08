; The town status screen (Training Grounds and tavern inspect): room for the help line.
;
; Each screen splits the 720 glyph sprites between four layers (0x800db3d0 takes the
; four sizes). This screen gives layer 1 seventy, and the five bold command labels under
; the help bar (Spellbook ... Sort Items, no digraphs in that font) take fifty of them,
; so with START's help on, a help line stopped after 20 glyph codes: "Spells can only be
; read here, not ca". Layer 0 holds the item list and the spell grid, 164 with six
; items and about 230 with eight long names, so twenty of its 346 move to layer 1.
; That gives the help line 40: the bar shows x = 18-332 and lines are centered on 168,
; so a line can be about 300 px, roughly 35 glyph codes (an overlong test line spilled
; past both ends of the bar rather than stopping).
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800cbec0
    addiu   a0, zero, 326       ; layer 0, was 346
    addiu   a1, zero, 90        ; layer 1, was 70
.close
