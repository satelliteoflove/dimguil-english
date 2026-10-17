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
0x800cbddc (tavern Inspect and Boltac's Inspect, 5 rows) and boltac_menu 0x800bae4c;
HAZURE edge_inspect 0x800a3f50, edge_identify_menu 0x800a9034, edge_use_item 0x800aa160.
(The Training Grounds' Inspect Character is a different screen with no command menu;
a breakpoint on 0x800d6b58 saw no calls there.)

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

## Corner brackets: the full spec

Chris left the box as it is for now (decisions.md 25) and may add the brackets later as a
choice on the Configuration screen. This is everything needed to build B, either on its
own or as that option. Nothing here is in `asm/`. Scripts and shots are in
`rips/re/work/cursorframe/` (`brackets_all_sheet.png` is the overview). The sketch below
was assembled over copies of the built overlays in `test/` and run in RAM there; the
block as printed here assembles to the same bytes (`test/docsketch/`).

### The look

The routine draws four GsSPRITEs (attribute 0x58000000: 4-bit, semi-transparent, mode 1,
which adds the texel onto the screen) from tpage 0xf (VRAM x 960, y 0), CLUT 0x1ea
(VRAM 0, 490), v fixed at 0xf0. Read from VRAM in a save state (`vramtex.py`, the same in
MAZE, JOUKA and HAZURE states), the texture is a 72 × 12 box outline in index 0xe, CLUT
0x815f (255, 82, 0, STP set); index 0 is 0x8000, black, so it adds nothing. The box runs
u 0-71, v 0xf0-0xfb, with its top line at v 0xf0, its bottom line at 0xfb, and the sides
in columns 0 and 71. Column 72 is the left edge of the next graphic (a box from v 0xec to
0xff at u 72-79), which the parts never reach. At the brackets' corners:

    v      u 0 1 2     u 69 70 71   (72)
    0xf0     e e e        e  e  e     e
    0xf1     e . .        .  .  e     e
    ...      (rows 0xf2-0xf7 the same)
    0xf8     e . .        .  .  e     e

The bracket table is x, y, w, h, u per part, offsets from the call's (x, y):

    00 00 03 09 00 | 5d 00 03 09 45 | 00 09 03 01 00 | 5d 09 03 01 45

The left part draws u 0-2 of rows 0xf0-0xf8, the right part u 69-71, both 9 rows from
y + 0. The ticks draw u 0-2 and u 69-71 of row 0xf0, one row, at y + 9. With the bias at
-0x79 instead of -0x78, everything moves up one pixel. For a cursor row whose label cell
is (0xde, y), y = 0xbc + 8n, the call is (0xd4, y) and the brackets come out as (screen
x; image x is 14 more in Beetle's 350 px frame):

    x      212 213 214  ...  305 306 307
    y-1     O   O   O         O   O   O     parts 0, 1: row 0xf0, the box's top line
    y       O   .   .         .   .   O     rows 0xf1-0xf8: column 0 / column 71
    ...                                     (y+1 to y+6 the same)
    y+7     O   .   .         .   .   O
    y+8     O   O   O         O   O   O     parts 2, 3: row 0xf0 again, as ticks

So each bracket is 10 px high, from one row above the label's 8 px cell to one row below
it, and 3 px wide, at the box's own left and right columns. That's 28 pixels against the
box's 204, all in the same orange and the same pulse (the routine sets the colour from
0x8007988c-e every call), which is why it reads fainter. The bars at y-1 and y+8 share
rows with the neighbouring labels' descenders and capitals, but only at x 212-214 and
305-307, where no label reaches (below).

The ticks use row 0xf0 because the routine has one v for all four parts (`addiu
v1,zero,0xf0` at 0x800e27e0 and its copies), and a part draws h rows down from v, so a
1 px part can only get row 0xf0. That row is the box's top line, solid from u 0 to 71, so
three texels of it make a tick. The texture's own bottom line (0xfb) is 11 rows down; a
part reaching it would draw the side to y+10. The original box gets its bottom line the
same way (parts 2 and 3: row 0xf0 at y+7).

### The routine's three copies

Disassembled from the built overlays (`rips/iso/dimguil/`, all loading at 0x800a1000),
the three copies are 190 instructions each and identical but for two words: +0x14, the
low half of the table's address (`addiu t8,v0,0x1ddc`, `0x17d8`, `0x127c`), and +0x90, a
`j` inside the routine. They're byte-identical to the original Rev 1 overlays, and so are
the three tables (`00 00 40 08 00 | 40 00 20 08 28 | 00 07 40 01 00 | 40 07 20 01 28`).

| Overlay | Routine R | Table | R+0x18-0x67 (table copy) | R+0x1cc (`addu a1,sp,v0`) | R+0x1ec (bias) |
|---|---|---|---|---|---|
| MAZE | 0x800e253c | 0x800a1ddc | 0x800e2554-0x800e25a3 | 0x800e2708 | 0x800e2728 |
| JOUKA | 0x800d6b58 | 0x800a17d8 | 0x800d6b70-0x800d6bbf | 0x800d6d24 | 0x800d6d44 |
| HAZURE | 0x800b9aa8 | 0x800a127c | 0x800b9ac0-0x800b9b0f | 0x800b9c74 | 0x800b9c94 |

Nothing else reads the tables: each overlay has one reference to its table's address
(the routine's +0x14), and no code file holds a pointer to a table or to a routine. The
only calls are the routine's own callers (MAZE 5, JOUKA 4, HAZURE 5 `jal`s). BATTLE,
MCARD and HAZURE run over other overlays' tails, but none of them calls a copy.

The routine copies the table to the stack with ten lwl/lwr pairs (R+0x18-0x67) and reads
the parts from there (`addu a1,sp,v0` at R+0x1cc). t5-t7 are used only by that copy, and
t8 only to point at the table, so the copy's 20 words are free if the parts are read
from the table directly. That room holds the choice of table and bias and the bracket
table itself, so the option needs no free space in these overlays.

**B on its own, no setting** (what the mock did): in each overlay, the table's 20 bytes
become the bracket table and the bias word becomes `0x2442ff87` (addiu v0,v0,-0x79).

**B as an option**: R+0x18 loads config[10] (0x80096382, see below) and picks the table
and bias; R+0x1cc becomes `addu a1,t8,v0` (0x03022821, was 0x03a22821); R+0x1ec becomes
`addu v0,v0,t5` (0x004d1021, was 0x2442ff88). The original tables stay where they are.
The armips is in the sketch below (`frame_style`). With config[10] = 0 the tavern status
screen's frame was pixel for pixel the one on the unpatched disc; with 1, the 28 above.

### Renders on every menu

All real renders on the English WIP disc (fb1cdfa): from states made on that disc, the
part table and bias written in RAM, then the cursor moved onto the row so the menu
redraws (`brackets_all.py`; it measures too). Every shot's orange pixels are exactly the
28 expected for its row (`check_shape.py`), and no label ink falls in the bracket
columns on any row. Label ink starts at x 222 or 223 on every menu (0xde, at least 7 px
clear of the left bracket's 214).

| Menu (caller) | Labels | Cursor shot on | Widest label, ink ends at | Clear of 305 |
|---|---|---|---|---|
| MAZE camp_inspect 0x800cf8dc | Cast Spell, Items, Pool Gold, Back | Cast Spell, Pool Gold | Cast Spell, 291 | 13 px |
| MAZE camp_items_menu 0x800d579c | Identify, Use, Give, Equip, Drop | Identify, Equip | Identify, 274 | 30 px |
| MAZE camp_use_item 0x800d7150 | the same submenu, redrawn on entering Use | Use | Identify, 274 | 30 px |
| JOUKA status screen 0x800cbddc, tavern Inspect | Spellbook, Equip Items, Give Items, Drop Items, Sort Items | Spellbook, Equip Items | Equip Items, 297 | 7 px |
| JOUKA status screen 0x800cbddc, Boltac's Inspect (0x800c400c) | the same | Equip Items, Sort Items | Equip Items, 297 | 7 px |
| JOUKA boltac_menu 0x800bae4c | Buy Items, Sell Items, Uncurse, Identify, Compare | Buy Items, Sell Items, Compare | Sell Items, 290 | 14 px |
| HAZURE edge_inspect 0x800a3f50 | Cast Spell, Items, Sort Items, Back | Cast Spell, Sort Items | Sort Items, 290 | 14 px |
| HAZURE edge_identify_menu 0x800a9034 | Identify, Use, Give, Equip, Drop | Identify, Equip | Identify, 276 | 28 px |
| HAZURE edge_use_item 0x800aa160 | the same submenu, redrawn on entering Use | Use | Identify, 276 | 28 px |

Every caller was reached. The labels are fixed strings at fixed x (e.g.
`items_menu_labels` 0x800e66a4), so the widths don't depend on the character; only the
greying changes (Identify for non-Bishops, Spellbook and Cast Spell for non-casters,
which is the case in these shots). On entering Use, both the submenu (0x800d5d10,
HAZURE 0x800a95f8) and the Use handler (0x800d7318, HAZURE 0x800aa33c) call the routine,
for the same row. The status screen calls it on every game frame while its menu has the
input (0x800cc3d4); the camp menus only when the cursor moves. Shots: `all/*.png`,
measurements `all/measure.json`, overview `brackets_all_sheet.png`.

### A Configuration-screen option

**Where.** Two copies of the same screen: Edge of Town > Change Settings (`edge_settings`,
HAZURE 0x800abbd4) and the camp's settings (`camp_settings`, MAZE 0x800d9304). A card
battle's SELECT screen (CMAIN 0x800aa904) is a separate screen with its own text; card
battles don't draw this frame, so it doesn't need the option.

**How the rows work** (code, both copies; HAZURE addresses, MAZE in brackets):
- A layout table of ten (x, y, string) halfwords, STATUS.OBJ 61 (CONFIGURATION), 62-69
  (the eight names) and 75 (Done), at 0x800a10a8 [0x800a1cbc]. The function copies it to
  the stack every frame and draws all ten once when the screen opens, on glyph layer 0.
  Names at x 80 (config_layout.asm), y 56 + 12n; Done at (172, 152).
- The options are straight-line code, five `text_at` calls a row ("(", value, "/", value,
  ")": SISETU 0x264, 0x25e-0x263, 0x217, 0x265) on layer 1, redrawn whenever the cursor
  moves, from 0x800abfd4 [0x800d96e4] to the `j` to the epilogue at 0x800ac588
  [0x800d9c98]. The value not chosen is dimmed by writing 7 to 0x80079760 before its
  call and 0 after.
- The cursor is the hand at (0xa0, n × 12 + 0x3b) (MAIN 0x80021840). Its byte is
  0x80079c5c [0x80079c5a], rows 0-8 with 8 = Done. It wraps at 0x800abe30 (`addiu
  v0,zero,8`) and 0x800abe40 (`slti v0,v0,9`) [0x800d9540, 0x800d9550]; circle on Done
  is tested at 0x800abe90 (`addiu v0,zero,8`) [0x800d95a0].
- Circle on rows 0-7 runs an if-chain on the cursor that flips one byte, 0x800ac5a0-
  0x800ac723 [0x800d9cb0-0x800d9e33], all ending at 0x800ac724 [0x800d9e34] (substate
  back to 1). Row 6 (Sound Effects) is config[7] and row 7 (Effects) config[6]. Since
  english_only.asm, rows 0-3 write 1 on both branches.

**Storage.** `config`, 12 bytes at 0x80096378: 0-3 the language switches (locked on 1),
4 sound output (1 stereo, 2 mono), 5 music, 6 effects, 7 sound effects, 8 message speed,
9 a card game flag (CMAIN writes it at 0x800b33b8 and 0x800b33e8 and reads it in five
places), 10 and 11 unused. A save holds all 12 at image 0x1eb5-0x1ec0, so config[10] is
image 0x1ebf. They're packed into the image in five
places (MAZE 0x800e5f34, JOUKA 0x800dab10, HAZURE 0x800bc008, MCARD 0x800aa518 and
0x800b26cc) and restored by MCARD 0x800aae88 and 0x800acbb4.

**The spare byte.** config[10] and config[11]: a scan of every code file
(`cfgscan.py`: immediates 0x6378-0x6383 and registers set to 0x80096378 used with
offsets of 8 and up) finds nothing that touches them but the save copies. Startup (MAIN
0x80032200) zeroes 0x800795b8-0x800a0baf, so they're 0 at power-on, and a save from the
original game should hold 0 there (nothing writes them). In the emulator, config[10] = 1
went through Suspend Game (01 at image 0x1ebf) and came back as 1 from Load Data after a
cold boot (`test/savetest.py`). A spare bit in the locked switches won't do: both load paths
store 0x01010101 over the first word. So 0 = box, the default and what every old save
says, and 1 = brackets.

**Room for a row.** Done is at y 152; a ninth row there puts Done at 164. The panel
(MAIN 0x800205b4 with 8, 0x10, 0x26, 0x1a) is dark down to about y 222, so there's room.
The names end by x 156 (Monster Names); the options run from x 0xa4 to the ")" at 0xf8
(0xfc on Sound Output). Both screens size glyph layer 1 at 154 and use 69 of it; the new
row is about 22. Shots: `all/edge_settings.png`, `all/camp_settings.png`.

**The original's labels near it.** STATUS.OBJ has Configuration labels the final game
never draws: 70 ヘルプメッセージ (Help Messages), 71 メッセージスピード (Message Speed),
72 オートセーブ (Autosave), 73 視点 (View, the viewpoint), 74 ステータスバーの表示 (Status Bar
display), and the option strings 76 (日本語／英語), 77 (ステレオ／モノラル), 78 (ON／OFF),
79 (常時表示／セレクトボタンで表示) and 80 (1 2 3 4 5 止まる). I found no code that draws
them (no text call with those numbers in the decompiled code, and the layout tables stop
at 69 and 75). Any of them could carry the new label, so no string has to be added; the sketch
uses 73.

**Label.** A proposal only: "Bracket Cursor" with the existing ( ON / OFF ), OFF being
the box. It's 75 px in the 12 px font, ending at x 155, just inside Monster Names. The
ON/OFF row layout is the Music row's, so the values line up with the rows above.

**The hook.** Everything stays inside the overlays that already hold the code:
- The frame routine reads config[10] on every call, in all three copies (above).
- Each settings screen gets one more cursor row: the two wrap values and the Done test
  go from 8 to 9, Done's y in the layout table from 152 to 164, the toggle chain's last
  test (0x800ac6f8 [0x800d9e08], row 7, which used to fall through for 8) branches to a
  new toggle for row 8, and the `j` after the last row is drawn goes to a routine that
  draws row 8 from a six-entry table and then jumps to the epilogue.
- The room for those comes from the rows 0-3 toggles. They're 44 words of if/else that
  now store 1 in every branch; one indexed store does the same in 7 words, leaving 37
  (0x800ac5bc-0x800ac657 [0x800d9ccc-0x800d9d67]). The toggle and the drawing take
  exactly 37.
- Free space elsewhere, for the record: the existing patches put new code at MAIN
  0x800159b8-0x80015bf3 (moved there from 0x80060e97, which turned out to be libds's
  play list; engine-notes "The VWF block and libds's play list") and
  0x80073a40-0x80073c74 (vwf.asm), 0x80073c78-0x80073cf4
  (catalog_vwf.asm), JOUKA 0x800a6c40 (bugfix_temple_lost.asm, an unreferenced debug
  menu) and several MCARD regions (the bugfix_* files). None is known in MAZE or HAZURE.
  Holding both tables in MAIN would work but splits the change between MAIN and the
  overlays, which the in-place version avoids (see the risks).

In RAM on the current disc (`test/ramtest.py`), with the sketch's bytes written into the
resident overlay: on both screens every row 0-7 changed the same byte as before (rows 0-3
none), row 8 flipped config[10] and its ON/OFF dimming, up from the top went to Done at
164, and after leaving, camp Inspect and Edge Inspect drew the brackets. The label read
"View", STATUS 73's current text.

The sketch, as one file (all of it has to agree, so it stays together):

```
; Menu cursor: the box or corner brackets, chosen on the Configuration screen.
; config[10] (0x80096382, saved at image 0x1ebf): 0 the box, 1 the brackets.
; Replaces english_only.asm's lock_toggles: remove both calls there in the same change,
; or that file (assembled after this one) writes its stores into the new row's code.
.psx

CONFIG_STYLE equ 0x80096382
LABEL_FILE   equ 0              ; STATUS.OBJ
LABEL_STR    equ 73             ; unused original label (視点); Chris's wording goes here

; The frame routine: pick the table and the bias from config[10]
.macro frame_style, file, routine
.open file, 0x800a1000
.org routine + 0x18             ; was the table's copy to the stack (ten lwl/lwr pairs)
.area 0x50, 0
    lui     t6, hi(CONFIG_STYLE)
    lbu     t6, lo(CONFIG_STYLE)(t6)
    addiu   t5, zero, -0x78     ; the box's y bias
    andi    t6, t6, 1
    beqz    t6, routine + 0x68  ; box: t8 already holds the original table
    nop
    lui     t8, hi(brackets)
    addiu   t8, t8, lo(brackets)
    b       routine + 0x68
    addiu   t5, zero, -0x79     ; brackets: one pixel higher
brackets:                       ; x, y, w, h, u: left edge, right edge, the two ticks
    .byte   0, 0, 3, 9, 0,  93, 0, 3, 9, 69,  0, 9, 3, 1, 0,  93, 9, 3, 1, 69
.endarea
.org routine + 0x1cc
    addu    a1, t8, v0          ; was addu a1, sp, v0: read the parts from the table
.org routine + 0x1ec
    addu    v0, v0, t5          ; was addiu v0, v0, -0x78
.close
.endmacro

frame_style "dirty/dimguil/MAZE.BIN", 0x800e253c
frame_style "dirty/dimguil/JOUKA.BIN", 0x800d6b58
frame_style "dirty/dimguil/HAZURE.BIN", 0x800b9aa8

; The settings screens: a ninth row, Done moves down one.
; lock:    the toggle chain's first test; v1 = the cursor, s1 = 1
; row4:    the chain's row-4 test (bne v1, v0 with v0 = 4)
; chain7:  its last test, row 7 (bne v1, v0, past the end)
; setsub:  where every toggle ends (lui v1, 0x8008, then substate 1)
; drawend: the j to the epilogue after the last row; s0 = 1, s3 = config,
;          s4 = 0x80079760 (the dim byte) there
.macro settings_row, file, text_at, wraplo, wraphi, done, layout, lock, row4, chain7, setsub, drawend, epilogue
.open file, 0x800a1000
.org wraplo
    addiu   v0, zero, 9         ; was 8: up from the top goes to Done
.org wraphi
    slti    v0, v0, 10          ; was 9
.org done
    addiu   v0, zero, 9         ; was 8: Done is row 9
.org layout + 9 * 6 + 2
    .halfword 164               ; Done's y, was 152
.org chain7
    bne     v1, v0, toggle_style
.org drawend
    j       draw_style
; Rows 0-3 only ever store 1 (locked on English); one store does it, which frees the
; rest of their 44 words.
.org lock
    sltiu   v0, v1, 4
    beqz    v0, row4
    addiu   v0, zero, 4         ; what the row-4 test expects
    lui     v0, 0x8009
    addu    v0, v0, v1
    j       setsub
    sb      s1, 0x6378(v0)      ; config[row] = 1
.area row4 - .
toggle_style:
    lui     v0, hi(CONFIG_STYLE)
    lbu     v1, lo(CONFIG_STYLE)(v0)
    nop
    xori    v1, v1, 1
    j       setsub
    sb      v1, lo(CONFIG_STYLE)(v0)
draw_style:
    lui     s1, hi(style_row)
    addiu   s1, s1, lo(style_row)
    addiu   s2, s1, 6 * 8
@@next:
    lbu     v1, 0xa(s3)         ; config[10]
    lh      v0, 6(s1)           ; dim this piece when config[10] is this (-1: never)
    andi    v1, v1, 1           ; bit 0, as the frame routine reads it
    lh      a0, 0(s1)
    bne     v0, v1, @@lit
    addiu   v0, zero, 7
    sb      v0, 0(s4)
@@lit:
    lh      a2, 2(s1)
    lh      a3, 4(s1)
    addiu   a1, zero, 152       ; the new row's y
    jal     text_at
    sw      s0, 0x10(sp)        ; layer 1, redrawn with the options
    sb      zero, 0(s4)
    addiu   s1, s1, 8
    bne     s1, s2, @@next
    nop
    j       epilogue            ; s1 and s2 are restored there
    nop
style_row:                      ; x, text file, string, dim when config[10] is
    .halfword 80,   LABEL_FILE, LABEL_STR, -1
    .halfword 0xa4, 4, 0x264, -1    ; (
    .halfword 0xb0, 4, 0x262, 0     ; ON
    .halfword 200,  4, 0x217, -1    ; /
    .halfword 0xd4, 4, 0x263, 1     ; OFF
    .halfword 0xf8, 4, 0x265, -1    ; )
.endarea
.close
.endmacro

settings_row "dirty/dimguil/HAZURE.BIN", 0x800bc99c, 0x800abe30, 0x800abe40, 0x800abe90, 0x800a10a8, 0x800ac5a0, 0x800ac658, 0x800ac6f8, 0x800ac724, 0x800ac588, 0x800ac730
settings_row "dirty/dimguil/MAZE.BIN",   0x800a1ecc, 0x800d9540, 0x800d9550, 0x800d95a0, 0x800a1cbc, 0x800d9cb0, 0x800d9d68, 0x800d9e08, 0x800d9e34, 0x800d9c98, 0x800d9e40
```

armips makes the labels inside a macro unique per call. The frame code takes 15 of its 20
words (the rest are zeros, nops); the settings code fills its 37 exactly.

### Risks and checks before building

- **The suite.** A disc with this has to pass a full suite round before `publish_test.sh`
  (`docs/harness-plan.md`, "The ratchet": the T2 trials, every saved case, and the
  cold-boot chapter 1 runs). The cases start from states with config[10] = 0 and none
  opens the settings screens, so the suite covers the box path and the overlays loading,
  not the brackets or the new row. On the built disc, also run `brackets_all.py --config
  --cue CUE` (it sets config[10] = 1 and leaves the code alone; then `check_shape.py`
  needs 28 pixels on every shot), walk all nine rows of both settings screens and check
  each changes its own byte, compare a box render with config[10] = 0 against the current
  disc pixel for pixel, and repeat `test/savetest.py`. The T5 screen check flags the box
  as drawing over glyphs on these menus today; with config[10] = 1 those findings should
  go away.
- **Save states.** A state keeps MAIN's code but loads overlays fresh, so a change split
  across MAIN and an overlay runs half old (the first voicing fix). This one changes no
  MAIN code. The frame routine and the settings code are in different overlays, but they
  agree only through config[10], a RAM byte. A state made before the change holds 0
  there, and any overlay still resident from it is old code drawing the box, which is
  what the new code draws for 0 too. Every part still goes in one file, because the
  settings code takes over english_only.asm's lock: if both files patch those words, the
  one assembled later wins (asm/*.asm go in name order after vwf.asm).
- **A bad save.** `save_data_reset` (MCARD 0x800ad018) doesn't clear config[10], so a
  corrupt save's byte stays. Both readers use bit 0, so the menus and the settings row
  agree whatever it is.
- **The label.** Reusing STATUS 73 changes an unused original string's English. Adding a
  new string instead depends on the text tools allowing it, which wasn't checked.
- **How it looks on the real renderer.** The brackets are 28 additive pixels; worth a
  look in the play-through setup (RetroArch, Beetle HW) before deciding the wording.

## Side note

Setting the original disc's own Configuration switches to English in RAM
(0x80096378-7b = 1) on the camp state, then opening Inspect, hung in the text expander
(0x8001e0b4-0x8001e414) with the panels blank (`jp_engmenus_hang.png`). That might be an
artifact of switching mid-session; it wasn't followed up.
