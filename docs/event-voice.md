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
| 見知らぬ古代文字が刻まれていた | Unfamiliar ancient letters are carved there: |
| 何か忘れてはいないだろうか? (colored, the party's own thought) | "Aren't we forgetting something?" |
| 何か必要なのであろうか? | "Do we need something?" |
| 特におかしな所はない | "There's nothing particularly strange about it." (or "here." when no object is named) |
| 触れてみますか? / 押してみますか? | Will you touch it? / Will you press it? |
| 「X」を手に入れた | Obtained X. |
| 太陽の石板 | TABLET OF THE SUN (the item's name; the developer's was LITHOGRAPH OF SUN) |
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
- **The Guardians.** Stiff and menacing, formal: "We are the Guardians who rule this
  land. You are not permitted to cut off the flow of the water." They call the party
  貴様ら; the English keeps a plain "you" and lets the formality carry the menace.
- **The Priestess's oracle.** Solemn and measured, set out in balanced pairs as in
  the Japanese: "You who know the nature of all things: do you see this place as
  one, or as all?" The three questions share one verb (見るか), so all three are "do you
  see... as...?". 伝える is "carry" both times: she carries the god's word, and you must
  carry the answer. 234 asks gently (持ち帰りなさい, "Take the proof home with you"); 236,
  for a party that believes in power alone, commands (持ち帰れ, "Take home the proof.").
  **Revisit in a later pass** (Chris, 2026-10-03): the oracle's wording was settled in
  S53 but may need another look.
- **The dome's voice and the inscriptions.** Terse commands: "Name the god!",
  "Correct! Let us begin!"
- **Otaka.** A goofy wandering adventurer who calls himself 俺っち and gives away
  items, a developer cameo. Chatty, silly and
  friendly, with sloppy grammar where the Japanese has sloppy writing: "What are the
  odds of bumping into you here! Name's Otaka, one of the programmers." His tildes stay
  where the Japanese has them ("Lessee~ what'd be good~"), as with Lychee. (プログ is short for
  programmer; the FAQ calls this a programmer's hidden event.) His friend Agan stays Agan.

## Puzzle text

Clues are translated exactly, never loosened: the vault hint ("North is 0 and South
is 180"), the escaping animals and their directions, the dial puzzle, the right and
left foot pillars, the stat door. The riddle's answer is still GAME, and the message
board that mentions a game of GAME stays, since it's a hint. The ancient-letter words
(DIMGUIL, SUN, STAR and so on) are already English and stay as they are.

One exception: the broken mural on Area B B1 (EV 215) spells MEATING in the original
glyphs, and the patch spells it MEETING (decided 2026-10-03). Before changing it we
looked for any sign the spelling was a deliberate joke and found none:
- Nothing near the mural (Area B B1 E17 N4) has to do with meat: no event, monster or
  item, and no line anywhere in the game ties that spot to food.
- The other glyph words are a set of the ship's room and system labels (BRIDGE,
  CONTROL, COCKPIT, REST, HEAL, REVIVAL, COLDSLEEP, TRANSPORTER, GAS, JUNK...). A
  meeting room fits that set; nothing in it is a galley or a food word.
- In katakana, meeting is ミーティング and meat is ミート. Both start ミー, so MEAT-ING is
  an easy slip when writing English from katakana. The same team misspelled monster
  names elsewhere ("Silhoutte", "Drumer", "Dragonare").
- The game's real jokes (TREBOR SUX, the DREAMLAND signs) are set up where the player
  sees them. This mural is "too damaged to make out", so a pun would have nothing to
  land on.
- harano's ancient-letter page and Emonoya's Dimguil tips don't mention the word, and
  web searches for it with the game's name turn up nothing.
- The player decodes the glyphs with the analysis item. Every letter of the word
  appears in 9 to 30 other strings (the A in 26), so no letter depended on this
  spelling. Only Z (FREEZER) and J (JUNK) come from a single word.

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
