# The menu cursor frame

The orange frame on the camp's Inspect menu (Cast Spell / Items / Pool Gold / Back) runs
through the tops of the bold letters and through descenders like the p of "Spell". This
note covers why, how the original disc looks, and what fixing it would take. Nothing is
patched. Shots and scripts: `rips/re/work/cursorframe/` (start with
`cursorframe_sheet.png`).

## The original does it too

On the original disc (Rev 1, state from `rips/re/work/P3-follow/jp/end.state`, camp >
Inspect > Earth) the frame sits in exactly the same place, y 188-195 for the first row,
and its top line runs through the top row of the kana: ア's top bar lies on it, and the
tops of じ, ゅ, も and so on touch it (`jp_current.png`, `jp_current_row1.png`). The kana
are 1 px strokes in rows 0-6 of the cell with row 7 empty, so the bottom line is clear
and the top overlap is easy to miss. The English labels are drawn in the original's own
bold Latin font (the party panel's "Jupiter" is the same on both discs but for a pixel
of the t, p descender in row 7 included): 2 px strokes, capitals and ascenders in rows 0-6,
descenders in row 7. So the top line hits every capital, and the bottom line hits p, q,
y and g. Same overlap as the original at the top; the bottom is new, and both show more
because the letters are heavy.

## The cause

The frame is drawn by one routine with three identical copies, one per overlay:

| Overlay | Routine | Part table | y bias (`addiu v0,v0,-0x78`) | v (`addiu v1,zero,0xf0`) |
|---|---|---|---|---|
| MAZE | 0x800e253c | 0x800a1ddc | 0x800e2728 | 0x800e27e0 |
| JOUKA | 0x800d6b58 | 0x800a17d8 | 0x800d6d44 | 0x800d6dfc |
| HAZURE | 0x800b9aa8 | 0x800a127c | 0x800b9c94 | 0x800b9d4c |

It's called as (0xd4, row × 8 + 0xbc) and puts four sprites from the table: five bytes
each, x, y, w, h, u, all offsets from the call's (x, y); v is fixed at 0xf0, tpage 0xf,
CLUT 0x1ea. The table is the same in all three:

    00 00 40 08 00 | 40 00 20 08 28 | 00 07 40 01 00 | 40 07 20 01 28

Parts 0 and 1 draw the texture's rows 0xf0-0xf7 (top line and sides; 64 + 32 px wide),
parts 2 and 3 draw row 0xf0 again one pixel high at y+7 as the bottom line. So the frame
is 8 px tall, y to y+7, which is exactly the label's 8 px cell: the labels are drawn at
(0xde, 0xbc + 8n), rows 8 px apart with no blank row between them. The frame's inside is
6 rows, the capitals are 7. No shift of text or frame can make them clear each other at
that size.

Callers, all with the same layout: MAZE camp_inspect 0x800cf8dc (4 rows),
camp_items_menu 0x800d579c (5), camp_use_item 0x800d7150; JOUKA the status screen
0x800cbddc (Training Grounds and tavern Inspect, 5 rows) and boltac_menu 0x800bae4c;
HAZURE edge_inspect 0x800a3f50, edge_identify_menu 0x800a9034, edge_use_item 0x800aa160.

Our patch changes none of it: no asm touches the routine, its table, the label positions
or the row spacing (vwf.asm's hooks in text_at only center horizontally). The labels with
descenders: Cast Spell, Spellbook, Equip Items, Equip, Identify, Compare.

The texture has side pixels below row 0xf7 too (0xf8 at least: `probe_h9.png`), so the
sides can be made taller from the table alone. Raising the top needs the y bias: the
table's offsets are unsigned bytes.

## Options

The renders are real: the emulator running the English WIP disc with the table and code
words rewritten in RAM, then the cursor moved so the menu is redrawn (the game doesn't
redraw it otherwise). C is an image edit of a render. All are in `cursorframe_sheet.png`.

**Leave it.** It matches the original at the top line. The descender hits are the only
thing the original didn't have.

**A: 9 px frame, top line one pixel higher** (`m1_tall9.png`, `m1_tall9_row1.png`). y bias
-0x78 to -0x79, and the bottom parts' y byte 7 to 8 (table +0x0b and +0x10), in all three
overlays: three code words and six bytes. The frame then runs y-1 to y+7 and clears
every capital and lowercase body. It still crosses descenders: its own label's on the
bottom line, and the label above's on the top line, since y-1 is that label's
descender row (the Items submenu with the cursor on Drop crosses Equip's q and p:
`items_m1_tall9.png`). Every screen that uses the routine changes the same way, and they
all share the layout, so nothing else moves.

**B: corner brackets** (`m3_brackets.png`, `m3_brackets_row1.png`). A new table: two
3 px wide, 9 px high parts for the left and right edges (u 0 and 69) and two 3 px
ticks at the bottom, plus the same -0x79 bias for symmetry. Twenty bytes and one word
per overlay. It clears every glyph on every screen, since the brackets sit left of the
labels' x (0xde) and right of the longest label. It's a different look from the
original's box, and fainter.

**C: rows 9 px apart and a 10 px frame** (`m4_pitch9_edit.png`, image edit). The only
option that clears everything and keeps the box. Costs: every label y on all eight menus
(immediates 0xbc, 0xc4... and two loops that compute n × 8 + 0xbc), and the cursor y at
14 call sites, where n × 8 + 0xbc becomes n × 9 + 0xbb, one instruction longer, so each
needs a hook into free space. Plus the table change (sides 9 high, bottom at +9) and the
-0x79 bias. Five rows starting at 0xbb end at y 230 with the frame's bottom at 231; the
panel's border is at 233, so it fits, just. Every menu above moves down and spreads out;
nothing else on those screens is placed against the rows as far as the code shows, but
each screen would need a look.

**A different font.** The labels have to be 8 px cells at 8 px spacing. The regular
font is 12 px, and the small 6 px font would fit inside the frame but reads poorly and
isn't used for menus anywhere else. Redrawing the bold font with 6 px capitals would
change every name and label in the game. Neither seems worth it.

## Side note

Setting the original disc's own Configuration switches to English in RAM
(0x80096378-7b = 1) on the camp state, then opening Inspect, hung in the text expander
(0x8001e0b4-0x8001e414) with the panels blank (`jp_engmenus_hang.png`). That might be an
artifact of switching mid-session; it wasn't followed up.
