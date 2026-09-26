# Event script voice sheet

EVENTMES.BIN holds the dungeon's event text: what the party finds, reads and touches,
the puzzles, and a few speakers. It's translated afresh from the Japanese. Terms follow
`terms.md`, item names follow the game's own English item list, and the box rules
are at the end.

## The narrator

Most of the script is narration. The Japanese is past tense and never names the
party ("the door began to open", "reached out a hand"). In English:

- **Past tense, no "you" unless needed.** "A huge mural covers the wall" for what's
  there, past tense for what happens: "The door slowly opened." Where English needs a
  subject, it's "you" or "the party", not "we".
- **Plain and a little old-fashioned**, like the text of the early Wizardry games.
  Short sentences, concrete words, no modern idiom.
- **Keep the dry jokes.** The Japanese sometimes undercuts itself ("You touched the
  monolith, but nothing happened. Or so it seemed."). Those stay.
- **Questions to the player** are short and end the box: "Touch it?", "Press the
  switch?"

## Recurring lines

| Japanese | English |
|---|---|
| 見知らぬ古代文字が刻まれていた | Strange ancient letters were carved there: |
| 何か忘れてはいないだろうか? (coloured, the party's own thought) | "Aren't we forgetting something?" |
| 何か必要なのであろうか? | "Do we need something?" |
| 特におかしな所はない | "Nothing unusual here." |
| 触れてみますか? / 押してみますか? | Touch it? / Press it? |
| 「X」を手に入れた | Obtained X. |
| 太陽の石板 | LITHOGRAPH OF SUN (the item's own name) |
| 巫女 | the Priestess (as in the King's speeches; her bracelet is the item RING OF MEDIUM) |
| 神殿 | the Shrine |
| 伝言板 | *Message Board* |

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
  items, and probably a developer cameo ("Otaka of Prog"). Chatty, silly and
  friendly, with sloppy grammar where the Japanese has sloppy writing: "Fancy running
  into you here! Name's Otaka, from Prog." His friend Agan stays Agan.

## Puzzle text

Clues are translated exactly, never loosened: the vault hint ("North is 0 and South
is 180"), the escaping animals and their directions, the dial puzzle, the right and
left foot pillars, the stat door. The riddle's answer is still GAME, and the message
board that mentions a game of GAME stays, since it's a hint. The ancient-letter words
(DIMGUIL, SUN, STAR and so on) are already English and stay as they are.

## The box

The event box looks like the dungeon text box from the Japanese line lengths: 288
pixels wide and 3 lines per page (to confirm in play).
`{ff26}` waits for a button and starts a new page. A `"` is only safe at the start of
a line, because the printer merges one that follows certain letter pairs into a
Japanese voicing mark. Inside a line, use `'`. `scripts/evfit.py` checks all of this.
The whole file should still fit in its original 25,721 bytes. The digraph compression
normally makes that easy.
