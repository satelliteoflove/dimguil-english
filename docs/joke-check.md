# Joke check (2026-11-03)

This check looked for humor the English adds that the Japanese doesn't carry. It was
prompted by Lilia's "seventeen and holding" (1:241 and 3:227). That line read a lie about
her age into ピチピチの17才よ, which the game doesn't support. Her party is 13-year-olds,
so she's plausibly really seventeen and the oldest.

Four agents read every string beside its Japanese:
- NPC_MES1-5: 1,150 strings.
- EVENTMES: 317 strings.
- SISETU: 673 strings.

They flagged:
- punchlines;
- borrowed catchphrases;
- comic idioms;
- sarcasm;
- winks;
- references and puns.

I then checked each finding against the review history. The item and monster
descriptions weren't re-read, because the Q1 sweep had already read them line by line
beside the Japanese. The brief and raw findings are in `rips/review/jokecheck/`, which
isn't committed.

## Added, and not yet settled

| Ref | Speaker | Japanese | Current English | Change |
|---|---|---|---|---|
| 1:241, 3:227 | Lilia | ピチピチの17才よ ("a fresh, bouncy seventeen") | "seventeen and holding" | Done: "fresh and seventeen" |
| 2:166, 3:266 | Reiran | それで? ("And?") | "And your point is...?" | Done: "And?" |
| 4:9 | Bergamot | 同じ年代かな? ("about the same age?") | "about our vintage?" | Done: "about our age?" |
| SISETU 144 | Boltac's clerk | それは武器じゃないのよ ("That isn't a weapon.") | "That isn't a weapon, dear." | Done: "That isn't a weapon." |

Notes on the table:
- 1:241: the first draft's rationale (commit aa257f1) called the line an "obvious,
  knowing age lie". Nothing in the game backs that. ピチピチ appears only in these two
  lines, and no one else comments on her age.
- 2:166: the others asked the same thing get plain renderings ("Yeah? So?", "And? So
  what?", "Oh yeah? So?"). Reiran's is the only set phrase.
- 4:9: 年代 is the plain word for an age group. The parallel age greetings carry no joke.
- SISETU 144: the clerk never addresses the player in lines 139-145. "dear" came in with
  576334d, with no note.

The "seventeen and holding" description has been taken out of `docs/npc-map.md`, the
announcement outline and the review scene summaries. `scripts/pubquotes.py` now flags
any quote in the README, CHANGELOG or release outlines that the translation used to have
but no longer does.

## Idioms Chris chose on purpose

Each of these takes an English idiom where the Japanese has a plainer phrase. Chris
asked for American phrasing on each one, and the stronger edge was pointed out when he
chose it. They're listed so the choice is on record, not as errors.

- **1:162 Alstron, "you can lead a horse to water."** The Japanese is 親切があだになる
  ("kindness can backfire"), a self-effacing sniff. The proverb casts the party as the
  stubborn horse, which is a sharper jab than the Japanese makes. Question 19 noted that
  it "needles harder". If revisited, the closest version that fits is "Well,
  kindness can sometimes do more harm than good."
- **1:74 and 3:47 Lilia, "bless their heart."** The mock-politeness is real. This is
  her only use of いらっしゃる, and it's laid over 頭の弱そうな ("weak in the head").
  The Southern formula carries the same irony (question 50).
  voice-lilia-3 replaced it with "a teeny bit slow. Are you gonna be okay?", because
  "bless their heart" is a Southern matron's phrase and she's seventeen.
- **2:144 Balbo, "Finders keepers, right?"** からな gives away their motive for
  hauling the bodies. Chris asked for it to be clear to Western readers (question 3). The
  catchphrase states it outright.
- **2:56 Rosea, "There. I said it."** This stands in for the deadpan さん after the
  "unsayable" name (scene npc-embarrassing-name). The Japanese has the punchline, and the
  English one is in a different form.
- **1:204 Guy, "Glad we cleared that up!"** This was one of three options for the
  breezy よろしくっ (question 40). It's a reading, not an error.

## Already in hand

3:28, Lilia's "It's a date." It's the copy of 1:40. Both now read "We'll meet again.
.........That's a promise." (voice-lilia-2).

## Cleared

The EVENTMES and SISETU jokes are all in the Japanese:
- MALOR into rock;
- TREBOR SUX;
- the dreamlands;
- "Or so it seems";
- Otaka;
- the recruits' self-mockery.

These lines were also cleared:
- EVENTMES 288, "satisfying click";
- SISETU 363, "bar tab";
- SISETU 369, the ninja's "I am, I am" (it renders ござる);
- SISETU 373, "rich brat" (it renders ボンボン).
