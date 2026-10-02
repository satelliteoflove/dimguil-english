# Event script voice sheet

EVENTMES.BIN holds the dungeon's event text: what the party finds, reads and touches,
the puzzles, and a few speakers. It's translated afresh from the Japanese. Terms follow
`terms.md`, item names follow the game's own English item list, and the box rules
are at the end.

## The narrator

Most of the script is narration. The Japanese mixes tenses freely (ている for what's
there, た for what happens) and never names the party ("the door began to open",
"reached out a hand"). Japanese readers don't notice the switching; English readers
do. In English:

- **Present tense, second person, all the way through**, as in a text adventure: "A
  square monolith stands on the altar." "You touch the monolith, but nothing happens."
  "The door slowly begins to open." This runs straight into the prompts ("Will you
  touch it?") without a jolt. Past tense only for what really happened earlier ("The
  switch you pressed earlier is still held down"). "Obtained X." is a status line and
  stays as it is. The subject is "you", never "we" (except the party's thoughts).
- **Prompts are full questions**: "Will you touch it?", "Will you press it?", not
  "Touch it?".
- **Plain and a little old-fashioned**, like the text of the early Wizardry games.
  Short sentences, concrete words, no modern idiom.
- **American English**, in idiom as well as spelling. The old-fashioned feel comes
  from plain, slightly formal wording, never from British turns of phrase ("fancy a",
  "rubbish", "lad"). The exception is a formal or stuffy speaker, where a British
  turn of phrase can be deliberate.
- **Full sentences.** No clipped fragments unless the speaker or scene really calls
  for them (Otaka's chatter, a terse inscription).
- **Keep the dry jokes.** The Japanese sometimes undercuts itself ("You touch the
  monolith, but nothing happens. Or so it seems."). Those stay.

## Recurring lines

| Japanese | English |
|---|---|
| 見知らぬ古代文字が刻まれていた | Strange ancient letters are carved there: |
| 何か忘れてはいないだろうか? (colored, the party's own thought) | "Aren't we forgetting something?" |
| 何か必要なのであろうか? | "Do we need something?" |
| 特におかしな所はない | "There's nothing particularly strange about it." (or "here." when no object is named) |
| 触れてみますか? / 押してみますか? | Will you touch it? / Will you press it? |
| 「X」を手に入れた | Obtained X. |
| 太陽の石板 | LITHOGRAPH OF SUN (the item's own name) |
| 巫女 | the Priestess (as in the King's speeches; her 腕輪 is the item RING OF MEDIUM, so the narration calls it a ring) |
| 神殿 | the Shrine |
| 伝言板 | *Message Board* |
| 魔物 | monster (not "fiend"; see `terms.md`) |
| 悪魔 | demon |

The coloured thoughts (`{ff30}2`) are the party thinking aloud, so they're the one
place "we" is used.

## Speakers

- **Message boards.** Notes from townsfolk, mostly to someone called Jade: casual,
  a little cheeky, signed or not as in the Japanese.
- **The Guardians.** Stiff and menacing, formal: "We are the Guardians, who rule this
  land. You shall not cut off the flow of the waters." They call the party 貴様ら,
  so no warmth at all.
- **The Priestess's oracle.** Solemn and measured, set out in balanced pairs as in
  the Japanese: "You who know the nature of all things: do you see this place as
  one, or as all?"
- **The dome's voice and the inscriptions.** Terse commands: "Name the god!",
  "Correct! Let us begin!"
- **Otaka.** A goofy wandering adventurer who calls himself 俺っち and gives away
  items, a developer cameo. Chatty, silly and
  friendly, with sloppy grammar where the Japanese has sloppy writing: "Fancy running
  into you here! Name's Otaka, one of the programmers." (プログ is short for
  programmer; the FAQ calls this a programmer's hidden event.) His friend Agan stays Agan.

## Puzzle text

Clues are translated exactly, never loosened: the vault hint ("North is 0 and South
is 180"), the escaping animals and their directions, the dial puzzle, the right and
left foot pillars, the stat door. The riddle's answer is still GAME, and the message
board that mentions a game of GAME stays, since it's a hint. The ancient-letter words
(DIMGUIL, SUN, STAR and so on) are already English and stay as they are.

Murals that carry an ancient-letter word describe the picture with that word, so the
player can guess the letters (a ship for SHIP, a figure like Death for DEATH).

とりもち is birdlime, the sticky paste used to trap birds. The dead bird in the
window (17) was caught in it, it gets on the party's hands, and later it holds a
switch down (44, 45). Most American players won't know the word "birdlime", so it's
"a sticky white paste" in 17 and "the sticky paste" after, which keeps the link
between the scenes.

## The box

The event box looks like the dungeon text box from the Japanese line lengths: 288
pixels wide and 3 lines per page (to confirm in play).
`{ff26}` waits for a button and starts a new page. A `"` is only safe at the start of
a line, because the printer merges one that follows certain letter pairs into a
Japanese voicing mark. Inside a line, use `'`. `scripts/evfit.py` checks all of this.
The whole file should still fit in its original 25,721 bytes. The digraph compression
normally makes that easy.
