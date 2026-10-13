# Unidentified flying monsters: "Bird" and the rest

Asked by Chris, 2026-10-13, after the harness saw an unidentified Wing Lizard group shown as
"4 Birds". These names are the disc's own English (the monster records in DATA02, see
`scripts/namefixes.py`); we have only fixed their typos and plurals. Nothing is changed
yet.

Source: Bartok's Trading Post, `data/monsters/dim/ps.json` (the unidentified name in
English and Japanese, and the unidentified picture each monster shows). The pictures are
the site's mapping; check them in the game before acting on them. A sheet of the four
pictures is at `rips/re/work/birdnames/silhouettes.png`.

## What the game does now

| Japanese | English on the disc | Monsters | Picture |
|---|---|---|---|
| はばたくかげ "flapping shadow" | Flap Insect(s) | Giant Mosquito, Dragon Fly, Faerie Fly | uk/03, an insect |
| | Bird(s) | Zopilote, Xecotcovach | uk/07, a winged serpent |
| | Bird(s) | Vampire Bat, Wing Lizard | uk/08, a bat-winged figure |
| | Flying Figure(s) | Fake Cupid, Holom-Tucur | uk/08 |
| | Flap Figure(s) | Camazotz | uk/08 |
| はばたくひとかげ "flapping human shadow" | Bird(s) | Were Vulture | uk/07 |
| | Bird(s) | Were Bat | uk/08 |
| | Flying Figure(s) | Halycon | uk/08 |
| きょだいなとり "giant bird" | Very Big Bird | Death Hawk | uk/22, a great winged demon |
| きょだいなあくま "giant demon" | Very Big Bird | Marchosias | uk/22 |
| | Greater Demon(s) | Greater Demon, Agares, Bael, Ahalmez, Ixpuztec | uk/22 and uk/20 |

So one Japanese name has four English names, and one English name, "Bird", covers both
Japanese names. The same bat-winged picture is called Birds, Flying Figures and Flap
Figures depending on the monster. Marchosias is the only きょだいなあくま not called
Greater Demon.

## The series

- Wizardry III: Strange Bird (Harpy, Vulture, and Were Vulture on the FC and Apple), Large
  Bird (Roc), Flying Insect (Stone Fly).
- Wizardry V: Flying Creature (Black Bat, Blackfly, Night Locust, Raven), Bird of Flames.
- Wizardry VI: Flying Insect (Dragonfly, Giant Mosquito).
- Wizardry VII: Black Bird (rooks, crows, vultures).
- Gaiden IV (SFC), the nearest relative: はばたくかげ is Flap Figure for everything,
  including the Bat, Crow, Sparrow, the bees and the faeries. Our Camazotz already
  follows it, which is why Flap Figure was kept on 2026-10-09
  (`translation-notes.md`).

The series uses "Bird" for actual birds, and not for bats, lizards or were-creatures.

## Options

**Leave it.** It's the developers' English, and our rule so far has been to fix only
typos and garbled names (`namefixes.py`). "Bird" for a flapping shape is a fair first
guess, and the oddness is mild.

**A: fix only where the English contradicts the Japanese** (four monsters).
- Marchosias: Very Big Bird to Greater Demon, like every other きょだいなあくま and its own
  demon picture.
- Were Vulture and Were Bat: Bird(s) to Flying Figure(s), like Halycon, the other
  はばたくひとかげ. This keeps the hint that it's person-shaped.
- "Bird" stays on the four animals of はばたくかげ.

**B: name by the picture the player sees.** Everything showing the bat-winged figure
(uk/08) becomes Flying Figure(s): Vampire Bat, Wing Lizard and Were Bat join Fake Cupid,
Halycon and Holom-Tucur. Camazotz keeps Flap Figure, per the October decision, or joins
them. "Bird" stays for the uk/07 monsters, which really are birds (Zopilote is a
vulture, and Xecotcovach is the Popol Vuh's eye-gouging bird), Were Vulture included.
Marchosias becomes Greater Demon as in A.

**C: one name per Japanese name**, Gaiden IV's rule.
- Every はばたくかげ becomes Flap Figure(s), apart from the three insects, which keep Flap
  Insect.
- Every はばたくひとかげ becomes Flying Figure(s).
- Marchosias becomes Greater Demon.
- "Bird" leaves the game except in Very Big Bird.
This changes the most, and loses the bird hint on the real birds.

I'd go with A. It's the smallest change, it only touches names that disagree with the
developers' own Japanese, and it keeps Bird where it fits.

## Doing it

- Every new name fits the 16-glyph slots: Flying Figures and Greater Demons are 14 each.
- `namefixes.py` matches on the whole slot's text, so "Bird" can't be replaced for some
  monsters and not others. The fix needs entries keyed by record instead, a small change.
  Check whether the same names appear in M_CATALG, MESSAGE.DAT or BATTLE.BIN, as the
  other name fixes do.
- The site shows unidentified names, so message the site session if any change.
- Check in the game that the pictures match the site's mapping, Death Hawk's demon
  picture especially.
