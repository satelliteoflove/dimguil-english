# Release notes outline: every change the patch makes to the game

Factual inventory for Chris to write the release notes, README section and romhacking.net
page from. Not prose for publishing. Built 2026-10-13 from the repo at 8c26893. Each item
gives a source in brackets. "bugs.md" is `docs/re/bugs.md`, "decisions" is
`docs/re/decisions.md`, "tn" is `docs/translation-notes.md`, "en" is
`docs/engine-notes.md`, "wn" is `docs/writeup-notes.md`, "dc" is
`docs/re/description-check.md`, "hp" is `docs/harness-plan.md`. Where the docs disagree,
the item says so. The full list of disagreements is at the end.

## 1. Bug fixes to the original game (13)

Each is original code, present on the Japanese disc. Commit hashes from `git log`.

1. **Guy's statue warning to a stranger.** Before: a party that hadn't met Guy got the trap
   warning "The room up ahead's got some crazy trap in it!" (1:89). Now: the stranger's
   copy of the statue speech (1:87). Checked by disassembly only.
   [bugs.md 1.1; asm/bugfix_guy_statue_line.asm; 29233ff]
2. **Rosea's Madi.** Before: a Madi heal came with her cancel line, "I see... Do take
   care." Now: her Madi line, "Oh my, how awful! ... There, all better." (2:134).
   [bugs.md 1.2; asm/bugfix_rosea_madi_line.asm; 54596b4]
3. **Cephala's healing table.** Before: every choice from block 11 up ran the next block:
   "out of magic" cast Dial and healed, stone/dead at stage 1 got the paralysis line and
   Dialko, paralysis got the poison line and Latumofis (not cured), HP heals one spell
   too strong, and so on. Now: lines and cures match; the missing "can't treat" uses
   3:138 (identical Japanese). [bugs.md 1.3; asm/bugfix_cephala_heal_table.asm; 34cd45c]
4. **Alstron's Madi (1:157).** Before: never cast; a poisoned or paralyzed member at full
   HP got "That one seems quite all right, I'd say." Now: cast at Guy's stages 2 and 3.
   Emulator: 8/8 runs each way. [bugs.md 1.4; asm/bugfix_alstron_madi.asm; 1976612]
5. **The pit scene's middle.** Before: the rescuer's voice from above and "Looks like
   help has arrived. If you'll excuse us, we'll go on ahead." (3:95-96, 99-100) never
   played. Now: played before the rescuer arrives. Disassembly only.
   [bugs.md 1.5; asm/bugfix_pit_scene.asm; 5b565b9]
6. **Fritillaria's "walkin' corpse" (5:17).** Before: the name was found by kill count
   instead of deaths, so it named the wrong member (usually roster character 0), and when
   both of her greetings applied, 5:17 never showed. Now: names the member with 10+
   deaths, and the coin flip works. Disassembly only.
   [bugs.md 1.6; asm/bugfix_fritillaria_corpse.asm; fc6158f]
7. **Cresson's speech after the control room (4:24-29).** Before: skipped for good by any
   party that had finished the Decipher table, which set the same flag. Now: plays.
   Disassembly only. [bugs.md 1.7; asm/bugfix_decipher_flag.asm; 3e36a06]
8. **Special chat topics rerolled.** Before: some special topics could never come up:
   Guy's area topics (1:195-210), Balbo's "about other parties" (2:174-187), two of
   Fontana's stage-1 specials (3:181-196). Now: they come up, kept 90% of the time like the
   other specials. Emulator (Guy only): 0 before, 20/22 after.
   [bugs.md 1.8; asm/bugfix_chat_specials.asm; a9ed605]
9. **Failed raise from ashes at the Temple.** Before: the party table scrambled (in the
   test, a current member dropped out and a non-member took her place); a fallen party
   could end up listing nobody who's there, so its bodies couldn't be found (that part
   inferred). Now: the party table is fixed up as every other deletion does.
   [bugs.md 1.9; asm/bugfix_temple_lost.asm; e4c0da7]
10. **BROKEN ITEM purge on entering town.** Before: purging a BROKEN ITEM zeroed the uses
    left on whatever sat in the tenth pack slot. Now: clears the emptied slot.
    [bugs.md 1.10; asm/bugfix_broken_item_state.asm; c717515]
11. **Pit scene with no rescuer (soft lock).** Before: a party in which nobody had met Guy,
    falling into the Area C pit while Guy was the rescuer, sat on an empty talk window for
    good (also on the original MCARD). Now: Balbo's party rescues them if a member has met
    Balbo, otherwise the man in armor; no new text. Only a party made entirely of
    characters who never met Guy can reach it. [bugs.md 2.8 (moved to group 1);
    decisions 7; asm/bugfix_pit_rescuer.asm; 5ff86d2]
12. **Pillar guardian soft lock. Exposed by our longer English text.** Before (on the
    English build): about 3% of pillar touches locked the game on "The pillar begins to
    shake ... attacks." with no input. The Japanese line finishes 78-94 frames before the
    dust settles, so the Japanese disc never hits it; ours is about three times as long.
    Now: the fight always starts. Found by the play harness. [bugs.md 1.11; en "Pillar
    guardians"; decisions 23; asm/bugfix_pillar_race.asm; c13dea2]
13. **Disc read stall in Sony's CD library (libds).** Before: rarely, any disc read could
    stall forever, seen as "You've met someone!" with no meeting, music playing, no
    input. Original library code, byte-identical on the Japanese disc. Our patch doesn't
    touch the library, but our text code changes frame timing and so moves which reads
    land in the window. The rate on the Japanese disc wasn't measured. Two locks in about
    60 hours of bot play; likelier in Beetle than on hardware. Now: queued commands are
    marked ready last. Found by the play harness. [bugs.md 1.12; en "CD reads";
    decisions 24; asm/bugfix_dspacket_race.asm; 0ef275c]

Exposed by the English: 12 directly (text length). 13 is timing-related to the patch's
code, not text length, and unmeasured on the Japanese disc. The other eleven are
independent of the translation.

How they were tested: emulator runs used RAM-write setups, not natural play (bugs.md "How
the fixes are checked"). 1, 5, 6 and 7 were checked by disassembly only; 2 and 3 by script
dump and patched bytes. 12 and 13 were also run in the harness on the built disc.

## 2. Reopened content

Reopened by decision (each reached by new code modeled on the game's own):

1. **Zaril's healing** (NPC_MES5 35-42, log line 114). His handler had no heal offer.
   Now: offered when someone is hurt or has a status, only on Talk presses where his sale
   doesn't come up: 25% of presses when no sale is possible, 12.5% when one is. His sale
   keeps its original odds. One healer: Dialko, Latumofis, Dialma, 20% "out of spells".
   [bugs.md 2.2; decisions 2; asm/bugfix_zaril_heal.asm; 9135ef5, then 98b0c5e]
2. **Guy's and Fontana's re-introductions** (NPC_MES1 134-139, NPC_MES3 117-123). Before:
   with only some members having met the leader, Guy replayed the full introductions and
   Fontana introduced nobody. Now: the short "didn't we do this already?" version, as
   Balbo's party has; newcomers are marked as having met them.
   [bugs.md 2.3; decisions 3; asm/bugfix_reintroductions.asm; 7498b1c]
3. **Cresson's "girls" and "my good fellows"** (NPC_MES4 19, 20). Before: every party was
   "boys". Now: no women "boys", only women "girls", mixed "my good fellows".
   [bugs.md 2.4; decisions 4; asm/bugfix_cresson_greeting.asm; 7166f5d]
4. **Fontana's chat about Zaril's new party** (NPC_MES3 197, 199-200). Now a ninth topic
   at Fontana's stage 3 (after the split) only; each other stage-3 topic goes from 12.5% to
   11.1%. Stages 1 and 2 unchanged. [bugs.md 2.5; decisions 5;
   asm/bugfix_fontana_chat8.asm; 7c99607]
5. **Reiran's cut-off line** (NPC_MES2 200). In the original an end-of-string code after
   her first sentence hid the rest; both pages now show. Text-file change, no code.
   [tn "Reiran's cut-off line"; c5dee12]

Lines heard for the first time because of a section 1 fix: Guy 1:87, Rosea 2:134, the pit
scene 3:95-96 and 99-100, Fritillaria 5:17 (in the cases it was missed), Cresson 4:24-29
(for Decipher-table parties), Alstron's Madi 1:157, the rerolled chat topics.

Left unused by decision (the notes say these go in the release notes):

6. **NPC identify service.** Rosea, Cephala and Cleo have a full "identify an item?"
   exchange and every party file has its log line, but no code offers it. Stays unused;
   "the lines exist and the service was never in the game." [bugs.md 2.1; decisions 1;
   tn "Decided and left"]
7. **Balbo's party's "heard that already"** (2:243-247, 253, log line 2:249). Answers a
   "tell them news" topic that doesn't exist. Stays unused. [bugs.md 2.6; decisions 6]
8. **Guy's second line-up** (1:128-133). Introduces Fritillaria and Lilia together, which
   no stage of his party has. Stays unused. [bugs.md 2.3; decisions 3; d61d5d8]
9. **Artemisia's line about Zaril** (3:198). Not part of Fontana's block 8; stays unused.
   [bugs.md 2.5]
10. **Cresson's fourth greeting branch** (4:21, or string 0x98). Its flag (`t6`) is never
    set and its purpose can't be recovered; stays unreachable. [bugs.md 2.4]
11. **Other untraced NPC strings** (1:45, 1:292, 2:5, 2:50, 3:198, 4:144-146, 5:20-25 and
    others). Not proven dead: they may come from computed stores. [bugs.md "Not bugs"]

Still waiting on a decision: nothing in decisions.md is open. ROADMAP's "Waiting on Chris"
paragraph still lists the identify service and Zaril's healing (see the disagreements).

## 3. Engine and display changes for English

What changes for the player.

1. **Variable-width font and centering** for the main text. Remisse's work (vwf.asm and
   the font sheet), kept; one font cell later changed for the card game arrow (item 16).
   [README "Origins"; asm/vwf.asm; graphics/]
2. **Even letter spacing in Boltac's catalog, the Monster Compendium and the card game.**
   Their renderer spaced single letters like letter pairs ("W ea p on s").
   [asm/catalog_vwf.asm; 249f928]
3. **Battle text word wrap.** Words move to the next line whole instead of breaking
   mid-word ("Cuautori wi / th LANCE."); no wrapped line starts or ends with a stray
   space. One leftover: see section 7. [asm/word_wrap.asm; bee305b, 71d14dd, 8c26893]
4. **No kana merges in English.** A `"` or the letter pair "w " no longer turns the glyph
   before it into a voiced kana ("how hard" printed "ズhard"); 91 event strings had one.
   [asm/voicing_marks.asm; 9a955ba]
5. **Event box shows its full text.** The maze event box ran out of glyph sprites (72,
   one per Japanese character); 48 event strings were cut. Now 144.
   [asm/event_window_pool.asm; 6dc52dd]
6. **Boltac's Trade captions shown in full** (were cut at 14 glyphs).
   [asm/shop_caption_layer.asm; f5d4e8f]
7. **Status screen help line shown in full** (was cut at 20 glyphs).
   [asm/status_text_pool.asm; 1bc0171, 6764806]
8. **Inn room help lines shown in full** ("Restores all HP for 10000G a").
   [asm/town_text_pool.asm; 8072cad, 210f6be]
9. **Training Maze sign shown in full**, with its box sized to 177 and the text
   reworded to fit (it stopped at "but as a b"). [asm/training_sign_pool.asm; ec26800; tn]
10. **Maze return prompt's triangle** sits in the gap in "Press △ to return to the
    Fortress City." instead of on "return". [asm/return_prompt_icon.asm; 3653a07]
11. **Item catalog: 5 lines under tall pictures** (was 4). The 55 tall item pictures were
    cut to 143 rows: 16 trimmed, 11 items moved up, 28 shrunk 1-9%. Graphics changed.
    [asm/catalog_tall_text.asm; scripts/itempics.py; 6d26caf; en "Item catalog"]
12. **Temple chant words spaced out** ("Murmur-" ran into "Chant-").
    [asm/temple_layout.asm; 4b09b08]
13. **Settings screen:** names left-aligned at x = 80 (were ragged; "Spell Names" ran into
    its "("); サウンドの有無 labelled "Music" (it switches off the music only); Sound
    Output options shown as "Str/Mon". [asm/config_layout.asm; 6e8f023, e1661ce, 0e3e732]
14. **Name entry opens on the Latin letters**, for Create Character and Change Name.
    [asm/name_entry_latin.asm; e6619cf, 9e6d80c]
15. **English only.** The four name/status language switches default to English and are
    locked there on all three settings screens; "Jpn" is shown dimmed; a save that says
    Japanese loads as English. Reason: the English font replaced the kana, so "Jpn" drew a
    jumble. [asm/english_defaults.asm, asm/english_only.asm; 1624fc8, 18ea18f; tn "English
    only"]
16. **Card game:** its strings converted (cb_strings.asm), unit names spelled as in the
    Compendium (b681cce), password counter reads "Left: 5", mode labels "AUT"/"MAN"
    instead of "AUTO"/"MANU" running together (7199a30), the level-up arrow draws as an
    arrow instead of "A" (ab1771f), spell names matched to the main game (f2c604e).
17. **NPC parties' names in battle** are English (the records had katakana in the English
    slots). [binary/NPT00-15.BIN.json; scripts/nptnames.py; 890c13b]
18. **Files moved on the disc.** Five files that outgrew their sectors (I_NAME_E,
    NPC_MES1-4) are appended at the end of the data track; EVENTMES grows into its own
    sector slack. Possible effect: slower NPC encounters (section 7).
    [scripts/relocate.py; ROADMAP "Disc layout"; en "Loading files"]
19. **Long strings held under the text buffer limit** (544 bytes), which avoids the
    original engine's "random cutoff" in long lines. Build check, no code change.
    [scripts/textbuf.py; 98aec10; en "Text buffer"]
20. **Event lines centered.** 26 event strings kept the Japanese padding on one side and
    printed off center. [tn "Event lines off center"; fc8eabc]
21. **NPC speech closes its quotes.** The Japanese opens with 「 and never closes; the
    English now closes quotes (1,064 strings). [tn "NPC speech closes its quotes"; b440faa]
22. **King's reward speeches paged** (322, 326, 327 had run 8-11 lines into a 3-4 line
    window). [afdc56b]
23. **Saves.** "As far as we know the patch doesn't touch the save format" (ROADMAP);
    not yet verified across versions. Emulator save states don't carry across versions.
    [ROADMAP "Playthrough"; README "Status"; en "Loading files"]

## 4. Corrections to the original's wrong text

The Japanese has these errors too; the English had copied them. Before/after captures in
`docs/shots/description-corrections/`. [tn "Description corrections"; dc; decisions 11]

Spell descriptions (STATUS, the spell bar; 0f0a69b, Bacortu d798054):

1. 421 Halito: 1-8 → 2-8 damage (2d4).
2. 423 Melito: 1-8 → 2-8 damage (2d4).
3. 426 Morlis: "AC +4, and held fast" → "startles a group; their AC +4" (nothing holds them).
4. 428 Cortu: "a wall that stops enemy spells" → "enemy spells fail more; stacks".
5. 429 Tzalik: 24-58 → 24-48 (24d2).
6. 430 Lahalito: 6-58 → 6-36 (6d6).
7. 434 Bacortu: "walls enemies off from casting" → "enemy spells may be sealed; stacks".
8. 435 Zilwan: 1000 → 255-2550 damage to one undead (255d10).
9. 436 Ladalto: 44-98 → 10-100 (10d10).
10. 437 Lazalik: 64-80 → 40-80 (40d2).
11. 441 Dios: heals 1-8 → 2-8 (2d4).
12. 442 Badios: 1-8 → 2-8 (2d4).
13. 459 Kadorto: "raises the dead or ash" → "may raise dead or ash; full HP" (camp roll can fail).
14. 461 Madial: "party heals 30-60" → "party 17-68; camp 10-50".
15. 480 Alikus: 80-130 → 48-144 (48d3).
16. 483 Sios: 1-10 → 2-4 mental damage (2d2).
17. 484 Diomas: heals 2-6 → 3-6 (3d2).
18. 486 Lios: 2-10 → 2-4 mental damage, group (2d2, same as Sios).
19. 492 Masios: 2-16 → 8-16 (8d2).
20. 497 Dalosto: 36-64 → 14-70 (14d5).
21. 501 Galtomas: 12-48 → 4-48 (4d12).
22. 502 Lasios: 9-72 → 8-72 (8d9).

Item descriptions (ITEM.DAT; da781e2, Holy Crown 0f6a811):

23. Winter Wand: "Madalto" → "Ladalto" (its battle spell).
24. Rod of Raising: "Nearly useless as a weapon" → "It's no bad weapon either" (3d8, to-hit +3).
25. Wand of Mystery: "no attack power" → "hits lightly, but often" (1d7+2, two extra swings).
26. Gem of Exorcism: "can't be hit by undead attacks" → "undead attacks do half damage".
27. PK Crystal: "nullify sword and magic attacks" → "can turn magic aside" (nothing against weapons).
28. Mythril Plate: "neutralizes all kinds of breath" → "blunts many kinds of breath".
29. Dragon Kite: "block all magic and breath" → "ward off magic and breath attacks".
30. Worst Sword: dropped "cuts your attacks" (no swing penalty).
31. Axe of Woe: dropped "so you lose attacks" (no swing penalty).
32. Holy Crown: "Clergy and any fighter type" → "Clergy can wear it, as can Fighters, Lords
    and Valkyries" (Samurai, Ninja, Ranger can't). [decisions 17]

Help text and Compendium:

33. SISETU 219, Luck: "disarming traps and dodging enemy attacks" → "weathering breath
    attacks and escaping traps". [decisions 18; c4b344d]
34. Compendium 7.16, 2-Head Snake: dropped "Worse still, it can drain levels." [a25c54c]

Our own mistranslation, not the original's (力 rendered as the Strength stat; 8ace280;
decisions 12):

35. Skull Dagger → "It hits harder and truer, and even adds attacks".
36. Mace of Power → "adds power and accuracy ... raises Strength itself".
37. Golden Axe → "It also hits harder and truer."

The disc's own English labels and names that were changed:

38. "Sane" → "Confused" for the confused status: STATUS 208 (status screen, Look for
    Companions), 627 (party panel "／Conf"), 197 (an unread reversed copy). Battle screens
    weren't checked. [decisions 14; tn; 48fd153]
39. "EVENT Item" → "Event Item" (SISETU 604, item details). Not seen on screen.
    [decisions 16; 8e03a3f]
40. Dragonare → Dragonaire (Wizardry V's spelling), card game included. [ba9b96d]
41. Old Drumer → Old Drummer. [ba9b96d]
42. DISPLASER ROBE → DISPLACER ROBE. [ba9b96d]
43. Small Silhoutte(s) → Small Shadow(s) (correct spelling doesn't fit the 16-glyph slot).
    [63a6291]
44. -y plurals: Dragon Flies, Faerie Flies, Vorpal Bunnies, Beauties, Stone Sentries. [bdd2903]
45. Mythical list: Shocitnal → Xochitonal, Oserotoru → Ocelotl, Inkuintori → Itzcuintli,
    Kuautori/Cuautori → Cuauhtli. [2dcc4fa]
46. Web Spiner → Web Spinner, Allo Saurus → Allosaurus. [7940121]
47. Sopirote → Zopilote, Uthiu → Utiu, Ispusteke → Ixpuztec, Neshuteper → Nextepehua,
    Tepeyoryotl → Tepeyollotl. [7940121]
48. Compendium "Stink Man" → Smelia, as in battle. [e053e3a]
49. B-PLATE OF GOODNESS → BREASTPLATE OF BOONS. [859fab6]
50. STEEL GLOVES → IRON GLOVES (items 1:150, 1:151 now say iron too). [6c01bd6]
51. LITHOGRAPH OF SUN → TABLET OF THE SUN. [8336160]
52. Card game spell names Kadolto, Nagura, Rios → Kadorto, Nagula, Lios. [f2c604e]
53. Card game unit names (Mupphy's Ghost, Were Jagger, Ixquics, Demon Inp, Dhurahang...)
    → the Compendium's spellings. [b681cce]

Note: the priest is "Alstron" in battle too; his battle record says アルストン (katakana,
not the disc's English). [tn "Alstron, not Alston"; 890c13b]

## 5. Deliberate choices left as they were

Decided "leave it", that a player might notice:

1. "has died of old age" (SISETU 65/66) though the character is Lost and deleted.
   [decisions 19]
2. Training Maze sign doesn't say a wipe there still halves gold and costs the front
   member's items (box full; the site documents it). [decisions 20]
3. Compendium lore: Smoke Demon "swords barely harm it" and Venus Man Trap "burns well
   with fire spells" have no support in the code (the site gives real resistances).
   [decisions 21]
4. Madalqua's battle lines "in freezing cold" (FIGHTMSG 179/185); its element is
   Tiltowait's, not cold. [decisions 22]
5. "Hits 1 times!" (FIGHTMSG 118): one string serves every count. Kept as a Wizardry
   tradition; tn says that's "from memory of the early games, not checked against a
   disc". [tn "Deliberate choices"; 43ad45e]
6. "Retrain?" kept (SISETU 167). Yes trains three years: level 4, three years older.
   [decisions 15]
7. "Magic Item" kept (already Title Case like its neighbors). [decisions 16]
8. Item descriptions stay silent about six curses (Queen's Whip, Soul Bow, Ring of Skulls,
   Cloak of Capricorn, Trollkin Ring, Sword of Swishes), restrictions and hidden powers.
   [decisions 17; dc "Cursed"]
9. NPC Kadorto warnings kept: five NPCs say their Kadorto may fail; it never does.
   [decisions 13; also section 6]
10. Developer and series names kept: Halycon (Wizardry V), Maelific (Wizardry I),
    NUNCHAKA (VI, VII), BENT STAFF (I), Flap Figure (Gaiden IV) and Flap Insect, Astro
    Zombie, Chany Mask, Death Hawk, Stone Head, Demon Liche, Dragon Liche, Goblin Canon.
    [tn "Halycon", "Five more", "The rest of the bestiary"]
11. Small Shadow(s) covers four different Japanese unidentified names, as the developer
    merged them. [tn "Misspelled names fixed"]
12. Long item names in the catalog list wrap and touch the next name (170 names); likely
    the same in the original. [tn "To revisit", last item]
13. Sios and Lios both roll 2d2 in the code (the group spell probably meant more); the
    text now says 2-4 for both, code unchanged. [dc "Wrong ranges"; inferred slip]
14. The Fire Rock's "water on a hot stone" proverb, the Guilty's joke and the Gremlin's
    first-person line kept as the Japanese has them. [tn "Kept on purpose"]

Original quirks judged harmless and not changed (unlikely to be noticed):

15. Duplicate greeting blocks nothing picks (Guy, Zaril): same lines play elsewhere.
    [bugs.md 2.7]
16. The town's stat recompute piles up to-hit and similar fields, but every battle
    rebuilds them first. [bugs.md 3.4]
17. Every spell has a 1% failure floor; `party_store_pos`, swapped mode bytes,
    `save_data_reset`, the Alchemist class-change spell formula. [bugs.md "Not bugs"]

## 6. Balance bugs kept (the hardcore mode list)

Kept to match the Japanese release; each a candidate for an optional "hardcore mode"
patch. Nothing is decided about whether that happens. [ROADMAP "Maybe later"]

1. **Wipe item loss.** One character, in practice the party's first position (or whoever
   handled a chest trap that wiped the party), has every item rolled six times (82% per
   ordinary item, 99.9% per rare, the Tablet of the Sun included); the others keep
   theirs. All lose half their gold. [bugs.md 3.1; decisions 8: "document it on the site;
   may revisit later"]
2. **Weapon effects ignore level.** The level adjustment (about 1 point per 4 levels,
   +30 / -20 at most) is computed and thrown away; effects land at flat odds.
   [bugs.md 3.2; decisions 9]
3. **Level drain's save is backwards.** A better save makes drain more likely (about 9%
   now for a level-5 character; about 91% if fixed). [bugs.md 3.3; decisions 10]
4. **NPC Kadorto never fails**, despite five NPCs' warnings; free, no VIT loss or aging,
   works on ashes. [C-talk.md §5; decisions 13]

## 7. Known issues still open

1. **Digraph that ends in a space** ("s ", "t ") keeps its space at the end of a wrapped
   battle line; removing it would need the digraph's letter. [en "Text printer", end;
   asm/word_wrap.asm header]
2. **NPC encounters may load more slowly**: NPC_MES1-4 and I_NAME_E sit at the end of
   the data track. The fix (shift later files instead) was decided 2026-10-07, not done.
   [GitHub issue #3; ROADMAP "Disc layout"]
3. **Not tested on a real PlayStation.** Tested in DuckStation and Beetle PSX.
   [GitHub issue #4; README]
4. **Some event text breaks oddly across lines and pages.** [GitHub issue #2; tn "One-word
   last lines", "Event 6"]
5. **No playthrough to the ending yet**; Chris's recorded play-through is in progress.
   [README "Status"; ROADMAP "Playthrough"]
6. **Review still in progress:** NPC dialogue review (npc-review.md, open questions
   listed there); item/monster descriptions, MESSAGE and combat verbs haven't had a full
   second look; menus and combat messages not extensively tested. [ROADMAP "Quality
   passes"; README]
7. **Translation items to revisit:** 迷宮 as "labyrinth" or "maze"; Giant Spider
   "arachne"; Anointed Mace; Demon's Staff; Amulet of Matokani; other uses of "comrade";
   Fontana's maze-encounter voice; events 234/236; event 288 (confirm in play).
   [tn "To revisit"; event-review.md "Still open", "To check in play"]
8. **Event page 309** ends on a page break with no wait, so the box clears at once; the
   Japanese is built the same way. [event-review.md "Real event box sweep"]
9. **English-only isn't stated yet** in README.md, docs/release-readme.txt or
   CHANGELOG.md (grep found no mention); ROADMAP and tn say it must be.
10. **Save carry-over between versions** not yet verified once, per ROADMAP; README says
    saves "have so far carried over". [ROADMAP "Playthrough"]
11. **NPC rescue fees** natural-play test listed as still to check; `docs/re/rescue-test.md`
    isn't in the repo. [ROADMAP "The game's code"; docs/re/README.md]
12. **Harness coverage gaps:** chapter 1 only; lock picking untested; Japanese-disc
    battles don't end cleanly in the harness, so comparisons are limited; the card game
    and Compendium aren't covered by the town crawler. [hp "T3 and T4", "T2"; wn "The
    town sweep"]
13. **ITEM.DAT 39, the shop's "∞",** is left untranslated and draws as a blank (per wn;
    not otherwise checked). [wn "The card game crawl"]
14. **Item claims not verified** against code: Wizard's Cone, Faerie Cap, Amulet of Evil,
    Ring of Solitude, Winged Boots. Some Compendium entries not mapped with confidence.
    [dc "Not verified"]
15. **Version not shown in game** (open question). [ROADMAP "Open questions"]

## 8. Testing done

The play harness (`docs/harness-plan.md`, code in `scripts/harness/`, a headless Beetle PSX
frontend in `scripts/emu.py`). Button presses from a cold boot; RAM is only read.

1. **T1:** text capture by breakpoint on the text expander works. Found message speed
   doesn't affect the main game; found "Hits 1 times!" (kept).
2. **T2:** the full chain (power-on, characters, party, maze, fight or talk, back to town)
   100/100, twice; every macro 100/100 (character creation 300/300). Found: "Oops!
   There's no trap.!!" (fixed 86e45de), wrapped battle lines starting with a space (fixed
   71d14dd), "brings down on" (now "bashes", 095e0c2).
3. **Regression suite ("ratchet"):** every stuck moment becomes a permanent case; a
   change is committed only if the whole suite passes. hp's table ends at round 10,
   185/185; bugs.md cites 187/187 and round 13. The cases and states live in gitignored
   `rips/`, so the suite isn't reproducible from the repo.
4. **T3:** one run through chapter 1 (party, 13 training trips to level 7, four pillars,
   sealed door) from a cold boot, no stuck points; 290,108 frames, 23 minutes.
5. **T4:** eight parties with different classes and seeds, all eight finished chapter 1
   (one on rerun); 230,000-360,000 frames each, about half an hour together. 386
   distinct strings seen, 227 shots.
6. **Game bugs found by the harness:** the pillar lock (section 1 item 12) and the disc
   read stall (item 13). After the pillar fix: 0 of 200 seeds hang at the bird and at the
   snake (11 of 200 hung before at the snake); eight chapter 1 runs on the built disc
   started all 32 pillar fights first try. After the CD fix: the replayed lock and 100
   timing shifts read normally; two chapter 1 runs made the same reads in the same frames.
7. **Wrap fix check:** 55 of 57 wrapped messages byte-identical, the other two lost a
   trailing space. [wn "A space left at the end"]
8. **Other machine sweeps:** all 317 event strings (492 pages) printed through the real
   event box (26 off-center found and fixed); about 3,000 town screens crawled from 12
   start states; the card game crawled; fit checkers run on every build (items, spells,
   NPC pages, event pages, battle lines, text buffer, training sign). [wn "Testing in the
   emulator"; tn]
9. **Code reading:** the game's rules read from the original disc's code with Ghidra
   (2026-10-10 and 11); every item, spell, Compendium and help description checked
   against records and code. [en; dc; wn "Reading the game's code"]
10. **Chris's play-through** on RetroArch with Beetle PSX HW, recorded, in progress.
    [ROADMAP "Playthrough"]

## 9. Credits and notices to remember

1. The original team's requests (2026-09-26): their translation is removed and must not
   come back, and they aren't to be credited. [ROADMAP "The original team's requests"]
2. Required notice, `docs/notice.txt`, on the README, every release page and the
   romhacking.net page: built on Remisse's dimguil-patcher (text dumper and inserter,
   compression, variable-width font); no LLMs used in Remisse's original code; Remisse had
   no role in this project; the original team doesn't endorse it. `scripts/mkrelease.py`
   adds it to the release notes and the zip's readme. [ROADMAP; README "Origins"]
3. Repo history was filtered so the original team's translation never appears; Remisse's
   commits and authorship stay; GPL-3.0; README points to the original repo.
   [ROADMAP "Project identity"]
4. AI disclosure as currently written: Claude did the first-pass machine translation,
   much of the research, and most of the tooling and patch code since Remisse's work.
   `docs/README.md` says the docs are working notes written with Claude; the README,
   changelog and release notes are Chris's. [README "How it was translated"; docs/README.md]
5. Venue rules noted: RetroGameTalk wants an "[AI-Assisted Translation]" tag and bans AI
   discussion in threads; RHDN text in third person. [docs/announcement-outline.md "Venue
   notes"]
6. Developer credit: developed by Access, published by ASCII (staff roll "©2000ASCII
   ©2000ACCESS"); Soliton and Thunder Stone aren't in the credits. [wn "Facts that needed
   checking"; 9bf5cb1]
7. Rev 1 only (Redump #60391); Track 1 MD5 9eeb5c508abb23c0e3538108b7755890; the
   original 2000 pressing has the same serial and barcode. [README "Playing it"]
8. The patch is English-only; the readme has to say so. [ROADMAP "Text coverage"; tn]
9. Game changes go up front in the README, release notes and romhacking.net page,
   including deliberate non-fixes such as the wipe's item loss. [ROADMAP "Game changes up
   front"]
10. Sources the notes cite for names and rules, if acknowledgement is wanted: Emonoya's
    pages and BBS, Bartok's Trading Post data, the GameFAQs Wizardry V bestiary, the Five
    Trials atwiki, the Online Nahuatl Dictionary, tk421.net item lists, harano's
    walkthrough, a June 2000 fan tally of recruits. [tn; en; event-review.md]

## Where the docs disagree

1. bugs.md's summary table says group 1 is "13 (12 fixed; 2.8 ... waiting on one choice)";
   2.8 is fixed (5ff86d2) and kept (decisions 7), so all 13 are fixed.
2. ROADMAP "The game's code" says "Ten are fixed" plus 1.11 and 1.12, and its list leaves
   out the pit rescuer (2.8). It still lists the identify service, Zaril's healing, the
   wipe and the description corrections as waiting on Chris; all were decided 2026-10-11/12.
   It lists bugs.md 2.7, 2.8, 3.3 and 3.4 as still to check; bugs.md has settled all four.
3. decisions.md's intro says "Ten clear bugs are already fixed".
4. engine-notes says group 1 is "ten clear bugs", the wipe is "left as is pending Chris's
   decision" (decided: keep), and the cut-looking content other than Zaril and the
   re-introductions "wait on Chris" (all decided).
5. translation-notes says decisions 14-16 (labels) are "still open for Chris"; all three
   are decided in decisions.md.
6. writeup-notes' pillar section calls the "You've met someone!" stall "Still open"; it
   was fixed in 0ef275c. Its triage count (10 clear, 8 cut, 4 balance, 7 harmless) differs
   from bugs.md's current table (13, 6, 3, 9) after reclassification.
7. harness-plan's T4 notes put the pillar lock down to pressing START on an exact frame
   and say it may share a cause with the "met someone" lock; bugs.md 1.11 and
   writeup-notes say START only shifted the dust's random seed, and 1.12 is a separate
   cause. harness-plan's suite table stops at round 10 (185/185); bugs.md cites 187/187
   and round 13.
8. bugs.md 1.11 and 1.12 give no commit hash; git has c13dea2 and 0ef275c.
9. Pillar lock rate: "about 3% of pillar events" (bugs.md, en) and "about one
   play-through in nine" (wn). Different measures, not a conflict, but worth using one.
10. The notice's origin: ROADMAP says the original team's requests; a comment in
    `scripts/mkrelease.py` says "Remisse asked for this on the repo and on every release
    page."
11. description-check.md says "Nothing here was checked in the emulator yet" at the top
    but later "Checked on the real screens of the built disc"; its summary table says no
    help-text errors, while its sweep found Luck (SISETU 219).
12. ROADMAP and docs/re/README.md point to `docs/re/rescue-test.md`, which isn't in the
    repo.
13. writeup-notes' first Zaril bullet says the heal check goes ahead of his sale; that was
    the first version (9135ef5), superseded by 98b0c5e (sale first), as its follow-up
    bullet and bugs.md 2.2 say.
