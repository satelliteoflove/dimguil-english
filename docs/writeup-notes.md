# Notes for a writeup: what was hard, and how it was solved

Raw material for a later writeup of the project. These are notes, not prose: what
went wrong or got in the way, how it showed up, what the cause turned out to be, what
fixed it, and the numbers. The writeup itself is Chris's to write. Add new entries as
they come up; the commits named here have the detail.

## The game's text limits

Each of these was a limit sized for Japanese that English ran into. Almost none of
them gave an error: text just stopped, vanished or came out wrong.

**Event text silently dropped (2026-10-04, d7b4e6d, 250cf32).**
- What happened: a test build went out with every event message still in Japanese.
- Cause: the event review had pushed EVENTMES.BIN 326 bytes past what the encoder
  allowed. The encoder printed "[ERROR] ... Ignoring translations." and carried on, and
  the build script only grepped for errors without stopping. The file's own checker
  had been comparing against the wrong number (the section length, 25,721) so it
  always said "over" and nobody believed it.
- Fix: the file sits in 14 sectors with 1,049 bytes of slack after it, and the game
  loads all 14 (checked by hijacking a loader in the emulator), so the encoder may use
  the slack. The build now stops on any encoder error. Lesson recorded as a rule: never
  publish a build until its whole log has been read and the result checked in the game.

**The "random cutoff" in long narrator lines (2026-10-04, 98aec10).**
- Seen: Remisse (the earlier patch's author) noted long lines cutting off at random.
- First theory, disproved: file growth.
- Cause: the game expands a whole string, every page of it, into a buffer at
  0x8008b400 before printing, and live data starts 576 bytes later. Anything past byte
  576 gets overwritten. Measured with filler strings: 557 bytes print whole; at 625,
  page 9 shows zeros where bytes 576-592 were.
- Fix: no code change needed; every string is held to 544 bytes (32 spare for inserted
  names) by `textbuf.py` in the build. The longest today is 445.

**Text drawn one sprite per letter (2026-10-04 and 05, f5d4e8f, 6dc52dd).**
- How the game draws text: every glyph is a sprite taken from a pool, and each screen
  splits 720 sprites into four pools when it opens. When a pool runs out, the text
  simply stops. No error, no wrap.
- Boltac's Trade screens: captions showed only their first 14 glyphs ("Choose an item
  to un", "Which weapon i"). The shop name and caption share a pool of 28, and "Boltac's
  Trading Post" takes 14 where the Japanese name took 7. Found by Claude while checking
  Remisse's cut-offs; Chris hadn't noticed it in play. Fix: that pool 28 -> 58, taken
  from one with room to spare (its measured peak was 130 of 270).
- The event box in the maze: Chris found ".........Sure enough, the" at the Shrine door,
  the very start of the game (the line ends "the door won't open."). The window routine
  sizes its pool as rows x columns, 3 x 24 = 72, one sprite per Japanese character. An
  English line of the same width takes up to about 35 glyphs. A scan found 48 event
  strings cut somewhere. Measured in the real box with test strings: spaces count, a
  line that scrolls off gives its sprites back, a new page frees them all. Fix: one
  instruction doubles the pool to 144; the game already reserves 400 for it, so nothing
  else loses room. The checkers now count glyphs, not just pixels.
- The NPC talk box drew a 181-glyph test page whole; the busiest real page uses 93.

**The spell bar (2026-10-04, 6cc6966).** The one-line spell description bar prints the
first 30 glyph codes and drops the rest, counted by code, not by pixel. All 84 fit;
`spellfit.py` keeps it that way.

**The item catalog (2026-10-04, 7e46b2f, 6d26caf, 92513dc).**
- Descriptions are 144 px wide, 7 lines under most pictures but only 5 under the 55
  tall ones (after moving the text up; 4 before).
- One catalog entry turned out to hold two items' descriptions separated by a
  terminator (the Battle Axe and the Nunchaka), so from item 25 on, description k
  belongs to item k+1. The fit checker had been counting both as one and reporting a
  problem that wasn't there.

**A quote mark that turns into Japanese (2026-09-25, 9713e23).** Glyph 0xb6 is `"` in
the English font, but it's also the Japanese voicing mark, and the printer merges it
into the glyph before it. After certain letter pairs whose code doubles as a kana
(`y ` is フ), a mid-line `"` prints as ブ. Only quotes that open a line are safe; quotes
inside a line use `'`, and `npcfit.py` catches the rest.

## Working without reading Japanese

- Chris doesn't read Japanese. Each line was shown literally, sentence by sentence,
  with its cultural context, and then a natural rendering. Scenes were reviewed with
  Chris one at a time, and every approved scene was its own commit.
- A plain dictionary wasn't enough. JMdict, the standard free one, gives あの人 only
  as "he, she, that person". It misses the sense that carries Rosea's line: a woman
  speaking of her husband or lover (Daijisen; English Wiktionary has it). The answer
  was to put researched, cited word notes first, with a confidence level, and the
  dictionaries second.
- Role language (役割語, Kinsui Satoshi's term): おぬし, じゃ, かしら and the like tell a
  Japanese reader at once what kind of character is talking. Each character got a
  voice sheet before translation, and the review tool explains these markers word by
  word.
- The terminal was a blocker for review (2026-10-04, 651c96a). Reading a scene line by
  line in chat made it hard to get a feel for the whole. That led to a browser tool:
  the whole scene in Japanese, Literal, Current and Faithful, a compare view with the
  changes marked and the reason for each, word notes and dictionaries on hover and
  click, and every line drawn in the game's own font on the real text box, with the
  fit checks live as you edit.
- The game's font in the browser: drawn by the game itself. Every glyph was printed in
  the real dialogue box in the emulator, and each page was shot twice, with and
  without the text. The pixels that differ are the glyphs, so the see-through box
  background drops out.

## Line breaks

- Our NPC lines are broken the way the Japanese is: a sentence or clause per line, and
  never ending a line on "a", "the" or "to". A greedy fill-the-line rewrap didn't match
  that (Chris noticed in the tool). The rewrap now breaks at sentence ends first, then
  commas, then evenly. Run over all 1,052 NPC strings, it reproduces 840 of the
  hand-broken ones (e575437).
- The game centers event text and left-aligns NPC talk under the speaker's name, as in
  the Japanese.

## Testing in the emulator

- A headless libretro frontend (`scripts/emu.py`) on a patched Beetle PSX core, with
  breakpoints, memory watches and code coverage, drove almost every measurement here.
- To test text in a box you can't easily reach, the file is rewritten in RAM as the
  game loads it, so the box prints test text. Pitfalls that cost time:
  - the disc load is still running when the file's header appears, so the test text
    has to be written again for a while after
  - the expander won't read past the file's original length, so test text goes over an
    existing string
  - event pages need their wait code or nothing prints
- Save states keep the old text and file tables, so states are remade after any build
  that moves files, and a code fix can be tested in an old state by writing the
  patched instruction into RAM.

## Facts that needed checking

- The developer credit (2026-10-04, 9bf5cb1). Some English sources name Soliton or
  Thunder Stone. The game's own staff roll, rendered from its image files, ends
  "PRODUCE ©2000ASCII ©2000ACCESS"; Japanese Wikipedia agrees (Access developed, ASCII
  published).
- Only Rev 1 (Redump #60391, the bug-fixed reprint) is supported. It has the same
  serial and barcode as the original pressing, so the box can't tell them apart.
