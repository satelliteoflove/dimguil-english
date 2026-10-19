# NPC dialogue scene map (NPC_MES1-5.OBJ)

This maps every string in the five NPC dialogue files to the scene or talk topic it
belongs to, says when and where it plays as far as the sources allow, and lists what
links it to other scenes, other files and the event script. It is the NPC companion to
`docs/event-map.md`. Use it while reviewing: before signing off a line, look up its
scene here and check the threads it belongs to (end of file), so the English keeps
every link the Japanese makes.

**Coverage:** all 1,150 strings are placed in a scene or topic below (NPC_MES1 304,
NPC_MES2 272, NPC_MES3 283, NPC_MES4 167, NPC_MES5 124), checked by script against the
ranges in the headings. "Placed" means grouped with its scene; many talk lines have no
known trigger, and those are marked as such.

## Sources and conventions

- **n:k** is NPC_MESn string k. **EV n** is EVENTMES string n; **S n** is a scene in
  `docs/event-map.md`. **WT ch. n** is a chapter of `docs/walkthrough-npcs.json`, which
  places many NPC strings along harano's walkthrough route. Flagged-scene numbers are
  those of the NPC review (`docs/npc-review.md`, reports in `rips/review/`).
- **Roster** is Emonoya's NPC party pages (dimm_21-23, mirrored in the site repo's
  `data/monsters/dim/ps.json`): sixteen parties (N0-N15, the disc's DATA02/NPT00-15),
  each with its members and the stretch of the game it appears in. They are the best
  source for *when* a party, and so a file, is in play. Emonoya's own spawn page says
  where NPCs appear is otherwise unknown, and that the magic circles in Area X are all
  NPC parties, not monsters.
- **Game** (the text itself), **Walkthrough** (harano, via WT), **Roster**, or
  **Inferred** (my reading, which could be wrong) is given for each claim about timing.
- **The trigger logic isn't decoded.** One file is loaded when a party is met (engine
  notes); what picks a string inside it (greeting variant, which talk line, which
  reaction) is in code nobody has traced. The talk menu's topics are known from the
  files' own labels, and lines are grouped under topics by their content and by their
  position in the file, which is consistent: each block runs one line per member in
  party order. Where a block's topic is a guess, it says so.
- Unnamed speaker tags (before you learn a name) and who they are, from the Japanese:
  - Man with a greatsword = Guy; Tall woman = Linaria; Tall man = Alstron; Hooded woman =
    Lychee; Short man = Fritillaria; Green-haired elf = Lilia.
  - Man in armor = Balbo; Wolfish man = Alba; Cat-eared woman = Rosea; Faerie with a
    katana = Reiran; Shaggy man = Gaura; Woman with a spear = Artemisia.
  - Young samurai (小さな侍, literally "small samurai") = Fontana; Big Dracon = Zaril;
    Little elf = Cephala.
  - Robed elf = Cleo; Robed man = Cresson; Old man = Bergamot.
  - Man's voice = Guy at the pit (3:95/99, Inferred from 3:101), Bergamot in the control
    room (4:48).
  - Mysterious figure (謎の人物) and Mysterious man (謎の男) in NPC_MES5 are not party
    members; see 5.10-5.13.

## How the files work

**One file per party, and members carry their lines.** Each file belongs to one party
"family", and when a member moves to another party, their personal lines are copied
into that party's file too. 90 strings are identical across files for this reason:
Lilia's lines are in NPC_MES1 and NPC_MES3, Fritillaria's in 1 and 5, Reiran's and
Artemisia's in 2 and 3, Gaura's in 2 and 5, Zaril's in 3 and 5. A fix to one copy has
to be made to the others (the review does this as "shared lines"). The full list of
identical pairs can be regenerated with the script under "Checking coverage" below.

**Every file has the same skeleton,** in roughly this order: first-meeting greetings
under unnamed tags, named greetings, farewells (with variants for when one of your party
is dead or lost), greetings that react to your party, the party's story scenes,
introductions, services (healing, identify, recovering bodies, selling an unidentified
item, a practice fight), the five talk topics, "you told me that already", and the menu
labels. The talk topics, from the labels (1:281-285 and the same in every file):

- **News:** "We asked if they had any news" (何か新しい情報はないか).
- **Told them:** "We told them everything we knew" (知っている限りの情報を伝えた). The
  replies are reactions, usually opening with a pause ("......").
- **About themselves:** "We asked them about themselves" (彼ら自身のこと).
- **Other parties:** "We asked about other parties."
- **Personal:** "We asked them something personal" (個人的なこと).
- Services and introductions have their own labels: healing, identify, rescue our
  comrades, "who they were" (彼らの事, which brings up the introductions).

## The cast and the rosters

**Guy's party** (NPC_MES1). Guy (Gaillardia), the self-styled Hero, a Lord in his
battle record; Linaria, Fighter; Alstron, Priest; Lychee, Mage; then a fifth member:
Fritillaria, Thief, later Lilia (Liliaceus), Bard. They read as a Dragon Quest III party
stranded in Wizardry (`docs/npc-translation.md`, "Guy's party and Dragon Quest III").
Roster:
- N0, the four, level 4: from first meeting until you enter the Underground Shrine. Guy
  says they have no Thief and need to scout one (1:257).
- N1, plus Fritillaria, level 7: Underground until you enter Area A, and again from
  Guy's rescue until you enter Area B. Fritillaria was "scouted special" (1:121).
- Absent from entering Area A until the Jail Ogre rescue (WT ch. 6, ch. 8): they are in
  the ogre's cage, and Guy is the only one alive (1:80).
- N2, Lilia replacing Fritillaria, level 9: Area B entry until mimicry mode is released.
- N3 and N4, the same five, levels 12 and 15: mimicry mode to Area Z, Area Z on.

**Balbo's party** (NPC_MES2). Balbo, dwarf, Evil Lord; Alba, Ranger, the "wolfish man";
Rosea, Bishop, half Felpurr ("cat-eared woman"); Reiran, Faerie Ninja; Gaura, the shaggy
Mage who wants to be a Samurai. Later Artemisia, Valkyrie. Balbo and Alba rescued Rosea
long ago (2:228). Alba lost his comrades in another dungeon (2:231). Roster:
- N5, level 6: first met at Shrine 3F E11 N6, the two-switch door (2:72-81); until
  Fontana's party splits.
- N6, same members, level 9: when isn't known.
- N7-N9, Balbo, Artemisia, Alba, Rosea (levels 8, 11, 15): from Fontana's split to
  Area C entry, to Area Z entry, and after. Reiran and Gaura have left.

**Fontana's party** (NPC_MES3). Fontana, 13, Samurai, real name Kikunoshin, whom Zaril
renamed after a hero from his homeland (3:221); Zaril, Dracon Lord; Artemisia, Valkyrie;
Lilia, Bard, "seventeen and holding", the oldest; Cephala (Euphorbia Leuco Cephala), 13,
Bishop. Artemisia, Fontana and Cephala are childhood friends (3:224). Roster:
- N10, level 3: first met at Shrine 4F E11 N10 (Inferred: the first-meeting speech,
  3:74); until you enter Area A.
- N11, same members, level 6: when isn't known.
- N12, Fontana, Artemisia, Lilia, Cephala, level 9: Area A entry until the split. **Odd:**
  Zaril is missing from this roster, yet he is present for the quarrel that causes the
  split (3:75-89). Either the roaming party leaves him out or the table is off;
  unresolved.
- N13, Fontana, Reiran, Cephala, level 13: after the split, and in Area B until Zaril's
  party is rescued.

**Zaril's party** (NPC_MES5). Zaril, Fritillaria, Gaura. N14, level 8: from their rescue
in Area B (S28) on. Fritillaria stays with Zaril because Zaril saved him when he was
paralyzed and abandoned (5:84; who abandoned him is left open, and Guy's party is the
obvious candidate). Gaura left Balbo for them (2:187).

**The scholars** (NPC_MES4). Cleo (Cleodendrum), elf Bishop, a monster naturalist;
Bergamot, gnome Priest, ancient writing and magic circles; Cresson, human Alchemist,
architecture. They live in the underground library (Underground B3F x8y6, WT ch. 3).
Cleo and Bergamot are secretly heretics who took the Priestess; Cresson was a captive
(4:24). N15 (level 24) is Cleo and Bergamot with four Arch-class Guardians, fought in
the Area E control room (S51, 4:44-55).

**Who moves where.** The quarrel in Area A (3:75-89, WT ch. 8) is the turning point
(harano: the NPC parties change after it): Zaril leaves Fontana; Reiran leaves Balbo
for Fontana (3:9, her alignment changed); Gaura leaves Balbo for Zaril; Artemisia moves
to Balbo; Lilia leaves Fontana and is in Guy's party from Area B on; Fritillaria leaves
Guy and is with Zaril after the Area B rescue. Lilia asks you, twice, whether you'd
like to scout her (1:266, 3:257), which sets up her move.

**Not party members.** The shadow and the mysterious man (5:103-111), and Agan (5:112),
speak through NPC_MES5. Otaka, the programmer cameo, is in the event script (S57).

## NPC_MES1: Guy's party

**1.1 First-meeting greetings, unnamed (0-15).** Flagged A (done).
When: the first meeting with each member, before introductions (Game). Two sets: 0-5
for the four-member party (N0) and 6-11 with a fifth member (N1/N2), then alternates.
Who: Guy 0-2, 6; Linaria 3, 7; Alstron 4, 8; Lychee 5, 9; Fritillaria 10, 12, 14;
Lilia 11, 13. 15 is Artemisia, who is never in Guy's party: probably unused (Inferred).
What: is your party after the Priestess too; 1 is Guy saying a hero doesn't
discriminate by alignment (the parties here keep to their own alignment). 12 has heard
of you; 13 asks not to be picked on over alignment.
Links: 1:12 = 5:4, 1:11 = 3:5, 1:14 = 1:291 = 5:14, 1:15 = 2:10 = 3:40.

**1.2 Named greetings (16-22).** Not flagged.
Guy 16-19 (19 is a bare "......", trigger unknown), Linaria 20, Alstron 21, Lychee 22.

**1.3 Farewells (23-40).** Not flagged.
Unnamed 23-28, named 29-34, longer named farewells 35-40 (Lilia's 40 "It's a date",
same as 3:28). Links: 1:27 = 5:7, 1:39 = 5:12.

**1.4 Farewells when one of yours is dead or lost (41-45).** Not flagged.
Each hopes {ff12} comes back to life; Lilia's 45 is shared with 3:27.

**1.5 Greetings that react to your party (46-79, 113-114).** Not flagged.
When: a greeting chosen by something about your party (Inferred from content; the
conditions aren't decoded). Linaria 46-52 (met at the tavern, a mixed Good-and-Evil
party, all-male or all-female); Alstron 53-64 (a new face in the lineup 56-57, a
character he drank with 58, a beautiful young lady 59, a character named 'A' 60, buying
out the shop 61, young and strong but smelling of the stables 62, "thieving scum, where
did you get that money" 64); Lychee 65-72 ('Mule' drinking alone at the tavern 68, old
characters 70-71, a name too embarrassing to say 72); Lilia 73-77 ('Richguy' 75);
Fritillaria 78-79 (kill count "murder squad", a character who keeps dying); Guy 113-114
(new face, the tavern).
Links: the joke names ('A', 'Mule', 'Richguy', 'Appraiser' 2:50) are tavern
characters; 1:74 = 3:47, 1:78-79 = 5:16-17 (flagged 5-3).

**1.6 The Jail Ogre rescue (80-85, 104).** Flagged F (done).
Where: Area A B4F, behind the Jail Ogre at x17y12 (Walkthrough; S24).
What: Guy, the only survivor and poisoned, thanks you for killing "that big green
brute" and asks for Ruby Slippers (80/81 named and unnamed; 82 the prompt; 83 you
refuse, 84 you have none, 85 you give them). 104 later: they lost all their items but
are back in the maze, and give you 10000 Gp (harano has 1,000,000 on one page).
Links: S24; Catalog (the ogre); 3:101 (Guy "owed you one" at the pit); the Roster's gap
while they are caged; 5:84 (Fritillaria abandoned while paralyzed, perhaps here).

**1.7 Guy's altar warning (86-88, 295).** Flagged E (done).
Where: outside the altar room, Shrine 2F (Inferred: WT ch. 2; the Fire Golem's altar,
S7). Guy alone, battered: touching the altar brought out a monster that killed everyone
but him, "the immortal hero". 86/88 named, 87/295 unnamed (the same speech).
Links: S7, S18 (the golem route); 4:50 (Cleo: we hid monsters at the altar); 4:125
(Cresson: beware the altars).

**1.8 Guy resting outside a trap room (89-93, 296).** Flagged E (done).
Where: unknown (WT "Not yet placed"). Guy insists he's just taking a breather; the room
ahead has "some crazy trap"; they go back to the castle. Candidates: the warp corridors
of the Underground, the Area B warp switches (S27), the rubbish-room pit (S36).

**1.9 Guy goes Evil, then Good again (94-97).** Flagged G (done).
When: unknown. 94 Guy killed a friendly monster while grinding and the party followed
him to Evil, and he likes it ("Approach as a friend... then strike"); 95-97 Lychee
befriended a Magical Rabbit and they're Good again.
Links: mirrors Balbo's flips (2:92-93, 203) and Zaril's wish to turn Evil (3:231,
249-250; 5:86, 89-90); Alstron was once Evil (1:205).

**1.10 The maze changes (98-103).** Flagged C (done).
When: after mimicry mode is released (S47, Game). Guy asks what happened to the maze;
Lychee: "It wasn't Lychee! I only kicked a teeny little rock." 98-100 unnamed, 101-103
named.
Links: S47; 2:90-91, 3:72-73, 4:22-23, 4:42-43 (everyone reacts).

**1.11 The sealed door (105-112).** Flagged D (done).
Where: the island, at the sun door in front of the Shrine (S3, WT ch. 1).
What: Guy calls the door locked; Alstron says it's a seal, opened with a tablet, and
that magical items are placed at regular points around a sealed thing; Guy wants the
short version. 112 the farewell.
Links: S2 (the four pillars), S3; the TABLET OF THE SUN.

**1.12 Introductions (115-141).** Flagged B (done).
115-127 the first introduction: Guy, "the hero from far across the sea", then Alstron
introduces the others, including Fritillaria (120-121) or Lilia (122-123) as "our newest
member"; Guy insists he's the leader, Alstron: "Sure. We'll leave it at that." 128-133
quick introductions for new faces ("my class is Hero", "call me Al-chan"). 134-141
repeat introductions ("Didn't I tell you already?").
Links: 1:123 = 1:133 = 3:114; 1:132 = 5:30, 5:122.

**1.13 Healing (142-162, 299).** Not flagged.
Guy 142-151 (Dialko, Latumofis, Dios, Dial, Dialma; "Really, I'm sorry"), Alstron
152-162 (adds Madi, Kadorto). 299 the menu label.

**1.14 Recovering your dead (163-166, 301).** Flagged H (done).
Guy offers to carry a wiped-out party of yours to the Temple; 165 "We'll just help
ourselves to our fee."
Links: 2:142-145 (Balbo's version), 3:151-154 (Fontana's).

**1.15 Selling an unidentified item (167-173, 298).** Not flagged.
Three unidentified items from a chest, one for {ff11}0 Gp. 170 the A-D menu (= 2:149,
3:158, 5:46). 298 "obtained an item".

**1.16 A practice fight (174-176, 303).** Not flagged.
174 Guy accepts a test of skill; 175 the prompt; 176 you back out. 303 "The party
suddenly vanished, leaving money lying at our feet": when isn't known (Inferred: after
beating or leaving a fight with them).

**1.17 Talk: news (177-188, 230-235, 242-247).** Not flagged.
177-182 Guy asks his party, nobody has anything; 183-188, 230-235, 242-247 three sets of
"nothing new", one per member. Which set plays when isn't known.

**1.18 Talk: told them (189-194, 224-229, 261-267).** Flagged K (done).
Three sets of reactions to your news. 261 Guy's is a non sequitur ("isn't this dungeon
way too big?"); 262-267 Linaria laughs at a klutz, Alstron "how very fortunate", Lilia
"don't you want to scout me? ...Kidding!" (266-267, the same as 3:257-258).

**1.19 Other parties: Fontana's (195-199).** Not flagged.
When: Area X, before the quarrel (WT ch. 6). A party of kids led by "a little Samurai...
Fontana?"; Alstron finds him level-headed; Lychee got an item from cute boys.
Links: 2:179-184, 4:105-107 (others on Fontana's party).

**1.20 Other parties: Balbo's (200-206).** Not flagged.
When: around the lake machine (WT ch. 4). Linaria: grave robbers led by a Lord, "same as
our leader"; Guy: "I'm not a Lord, I'm a Hero!"; Alstron was once Evil himself; Lychee:
a pirate-looking guy.
Links: 3:190-196, 4:100-104, 5:63-66.

**1.21 Other parties: Zaril's split (207-210).** Not flagged.
When: after the quarrel (WT ch. 9). The young Samurai's Dracon formed his own party;
Alstron: only two companions, "how very reckless"; Lychee: Zaril asked her to join and
she said no.
Links: 3:75-89; 2:185-187, 3:197-200, 4:108-110.

**1.22 Other parties: the scholars (211-217).** Not flagged.
When: around the library (WT ch. 3). Guy recommends them; Lychee: "an old guy called
Cleo", couldn't understand a word; Lilia liked the elf gentleman.
Links: 2:188-194, 3:201-206, 5:67-69; 1:216 = 3:204.

**1.23 Other parties: the shady man (218-223).** Flagged I (done).
When: Area B, about the north-door shadow (Inferred, WT ch. 10). A shady man who left
without a word, oozing killing intent; Alstron starts to guess and stops himself.
Links: the shadow thread (end of file); 1:223 = 3:213.

**1.24 Talk: about themselves and personal (236-241, 248-260).** Flagged J (done).
Which block is "about themselves" and which "personal" isn't known. 236-241: Guy on gear
prices, Linaria a great cook, Alstron and the Book of Satori (238, the Dragon Quest III
reference), Lychee into summoning, Fritillaria wants his own party, Lilia "seventeen and
holding". 248-260: Guy good with fire and lightning (a hero's spells), Linaria starving
in dungeons (249) and "do you think monsters taste good?" (258), Alstron best at death
curses, Lychee's broom and her Greater Demon (260), Fritillaria bad at disarming traps
and hit when he fails (254), Lilia also dances, Guy needs a Thief (257), Alstron found a
"card" (259).
Links: 3:252 (Lilia: is it true some people eat monsters? A callback to Linaria);
2:60, 3:62 (the Card Master); 5:84 (Fritillaria abandoned); 1:240 vs 5:78.

**1.25 You told me that already (268-273).** Not flagged.

**1.26 The King's title, after the ending (274-280).** Not flagged.
When: after the ending, when your party carries the King's title (Inferred: SISETU 322
awards a title, and 276 "So that's what the King gave you"). They ask to see it;
Alstron: "Then you know everything"; Guy declines to be told, since they haven't heard
of the Priestess coming back; Lilia: you know more than we do now.
Links: S53, SISETU 322.

**1.27 Menu labels (281-285, 299-302).** The five talk topics and the services.

**1.28 Guy's puzzle hints (286-289).** Flagged L (done).
286 the Shrine looked like four floors but they can't find the stairs, a hidden door
(Shrine 3F, WT ch. 2); 287 since the maze changed, a device in a hidden room asks
questions, he'll ask the Fortune Teller (the GAME dome, S49); 288 the three-ring disc,
"three animals" (S33, WT ch. 10); 289 baffling glyphs on a higher floor, "that altar
room?" (the god's name, S45).
Links: 2:84-89, 2:261-263 (Balbo's), 3:278 (Fontana's god-word), SISETU Fortune Teller.

**1.29 Fritillaria's and Lilia's greetings (290-294, 297).** Not flagged.
290-292 Fritillaria (= 5:13-15), 293-294 Lilia (= 3:44-45). 297 Fritillaria "I can't
make sense of any of it": topic unknown (Inferred: his reply in the puzzle-hint or
told-them set).

## NPC_MES2: Balbo's party

**2.1 Greetings (0-20).** Flagged 7 (13, 22).
Man in armor 0-2 (1 "brother" for a same-alignment party, Inferred), Balbo 3-6 (5 "ain't
got no business with you lot"), Woman with a spear 7-8 and Artemisia 9-12 (late game),
Wolfish man 13 (Alba), Cat-eared woman 14 (Rosea), Faerie with a katana 15 (Reiran),
Shaggy man 16 (Gaura), named 17-20.
Links: 2:7 = 3:4, 2:15 = 3:10, 2:16 = 5:3.

**2.2 Farewells (21-33).** Not flagged.
Unnamed 21-26, named 27-33.

**2.3 Farewells when one of yours is dead or lost (34-46).** Flagged 4 (open).
Balbo hopes {ff12} makes it back, then "listen to me goin' all soft" (34-35); Alba will
pray (36-37); Rosea (38-39); Reiran: "technically your friend, right?" (40-41); Gaura
stammers (42-43); Artemisia's "see each other again" fluster (44-46).
Links: 2:40-41 = 3:32, 31; 2:43 = 5:11; 2:44-45 = 3:25-26.

**2.4 Greetings that react to your party (47-71).** Flagged 8 (70; open).
Alba 47-51 (Evil-only gear "don't turn Good", 'Appraiser' lonely at the tavern), Rosea
52-57 (Loktofeit warning 54, someone lost 55, an embarrassing name 56, "I could fall for
you" 57), Reiran 58-64 (the Card Master's complete set 60, old folks, a young Ninja with
a Thieves Dagger), Gaura 65-66, Artemisia 67-71 (age unknown 70, training juniors 71).
Links: 2:59-63 = 3:61-65; 2:67 = 3:39; 2:71 = 3:43; 2:65-66 = 5:18-19; 1:72 (Lychee's
embarrassing-name line) and 2:56 are the same joke.

**2.5 The two-switch door (72-81).** Flagged 9 (open); 81 also in flagged 3.
Where: Shrine 3F E11 N6 (Roster; S4). A man in armor needs the other switch pressed at
the same time (72-74 for any party, 75-78 for an Evil party, who mustn't sneak ahead);
79-80 the countdown and the click (the same Japanese as EV 301-302); 81 later, thanks.
Links: S4; EV 42-45, 301-302.

**2.6 Progress report: the blue stone (82-83).** Flagged 3 (open).
Where: Underground B2F x3y14, across the waterway (WT ch. 4). They too fitted the blue
stone into the TABLET and will search ahead. Links: S14, S15.

**2.7 Progress report: the center of something (84-85).** Flagged 3 (open).
Where: Area X, the central computer (S19, WT ch. 6). Four doors that won't budge, the
small tablets hold a secret; "don't interrupt our strategy meeting".
Links: S19; 4:30-41 (the scholars at the same tablets); 3:67-71.

**2.8 Progress report: the iron bars (86-87).** Flagged 3 (open).
Where: the Jail Ogre's cage, Area A B4F (S24, WT ch. 8). They go home by Malor to come
back prepared. Links: S24; 1:80.

**2.9 Progress report: the three discs (88-89).** Flagged 3 (open).
Where: the three-ring dial, Area B (S33, WT ch. 10). Links: S16 ("the sky fell", the
clue); 1:288.

**2.10 The maze changes (90-91).** Not flagged (the reports' voice issue doesn't apply:
this one is in Balbo's own voice).
When: after mimicry mode (S47). "Guess we gotta redo our maps."
Links: 1:98-103, 3:72-73, 4:22-23.

**2.11 Balbo's alignment flips (92-93, 203).** Flagged 1 (done).
92 poisoned, he let a friendly monster go, turned Good, and is repenting at the Temple;
93 he killed one by accident and is back to his old ways. 203 (about himself) he wasn't
always Evil. When: unknown.
Links: 1:94-97; 3:231, 249-250; 5:86, 89-90 (Zaril wants to be like Balbo).

**2.12 Lineup-change greetings (94-95).** Not flagged.
"Got yerselves a whole buncha new faces"; "Still breathin', are ya?"

**2.13 Introductions (96-113, 271).** Not flagged.
First 96-101 (Balbo, Alba, Rosea, Reiran, Gaura, Artemisia), with class 102-107 (Alba
"With a bow, I have no equal", Rosea "Leave identifying to me", Reiran "Shall I lop your
head off for you?"), repeats 108-113. 271 Artemisia's introduction under her unnamed tag.
Links: 2:107 = 3:113, 2:113 = 3:119; 2:103 sets up 2:227.

**2.14 Healing (114-135, 267).** Flagged 5 (123) and 6 (124-141), open.
Balbo 114-123 (Madial is the best he's got), Rosea 124-135 (130: revival at the Temple
has better odds, the Kadorto warning flagged as a mistranslation).

**2.15 Identify (136-141, 268).** Flagged 6 (open).
Rosea; 139 a failure curses the item.

**2.16 Recovering your dead (142-145, 269).** Flagged 5 (open).
Balbo: "We Evil types don't usually go in for this"; 144 "That lot had some mighty fine
gear on 'em." Links: 1:163-166, 3:151-154.

**2.17 Selling an unidentified item (146-152, 266).** Not flagged.

**2.18 A practice fight (153-155).** Not flagged.
Balbo is happy to fight; "gutless cowards" if you back out.

**2.19 Talk: news (156-161, 210-214, 221-225).** Not flagged.
Three sets of "nothing": Balbo "Figure it out yourself", Alba "Tiresome", Gaura asleep,
Reiran "isn't there anything fun to do?", Rosea "It's quiet, isn't it".
Links: 2:159 = 5:56, 2:160-161 = 3:265, 168; 2:213 = 5:76, 2:214 = 3:268; 2:224 = 5:85,
2:225 = 3:270.

**2.20 Talk: told them (162-167, 215-220).** Not flagged; 216 is context for flagged 2.
Reactions. 216 Alba: the smallest lapse can cost you your life; 218 Gaura is jealous of
everyone; 219-220 Reiran resolves to try hard too.

**2.21 Talk: about themselves, refused (168-173).** Flagged 8 (173) and 2 (169 context).
When asked about themselves: Balbo "That'll cost ya", Alba "Better that you not know",
Rosea "What's gotten into you?", Reiran "Ew. Creepy." Topic Inferred from the parallel
blocks in 3:176-180 and 5:92.

**2.22 Other parties: Guy (174-178).** Not flagged.
A "champion-of-justice type", "a man who styles himself a hero", Rosea knows his name,
Gaillardia.

**2.23 Other parties: Fontana (179-184).** Flagged 2 (180; open).
Balbo: born with a silver spoon; 180 Alba worries the young party won't be all right;
Rosea: Fontana, level-headed; Reiran: "that party's kinda sketchy... in more ways than
one".
Links: Alba's past (2.29); 1:195-199.

**2.24 Other parties: Zaril's split (185-187).** Not flagged.
When: after the quarrel. A party of three, one of them used to be Balbo's (Gaura); Alba
on the samurai boy's group splitting; Rosea relieved Gaura seemed well.
Links: 3:75-89; 1:207-210, 4:108-110; 5:66 (Gaura ran away from Balbo).

**2.25 Other parties: the scholars (188-194).** Not flagged.
Balbo: they know all about the Shrine but won't tell you squat; Artemisia: "an old
scholar guy... Cleo?" (= 3:203).
Links: 4 (the reveal); 2:192 = 5:69.

**2.26 Other parties: the stranger (195-202).** Flagged 8 (199; open).
Balbo: a stuck-up loner, no adventurer; Alba: fearsome bloodlust, no ordinary man;
Rosea: came into the Shrine alone; Gaura: scary man, grumbling; Reiran: he goes
"Begone!" (200, the shadow's own word, 5:105); Artemisia: creepy (201-202 = 3:211-212).
Links: the shadow thread; 2:199 = 5:73.

**2.27 Talk: about themselves (203-209).** Not flagged; 204 context for flagged 2.
Balbo wasn't always Evil (203); Alba is a Ranger "at present" (204); Rosea: no
half-bloods in this country? (205); Gaura: "me, not picky, good guy"; Reiran is 18;
Artemisia forgets she already told you her name, "I'm a Valkyrie!" (208-209).
Links: 2:239-240 (Rosea is half Felpurr); 2:206 = 5:79; 2:207 = 3:269.

**2.28 Talk: personal (226-242).** Flagged 2 (227-233 context; 233 open).
Balbo a heck of a swimmer, nowhere to swim (226); Alba better with katana and sword than
the bow he boasts of (227); Rosea was saved by Balbo and Alba (228); Gaura slow but great
otherwise (229); Reiran has a sword master teaching her (230); Balbo on Alba's lost
comrades (231); Alba "......" (232); Rosea wants to take his pain away (233); Gaura will
be a Samurai (234); Reiran sets off teleporters on purpose (235); Balbo: an untouched
shrine should have treasure (236-237); Alba: the Training Maze's strong monsters (238);
Rosea is half Felpurr and embarrassed (239-240); Gaura will get Muramasa (241); Reiran
wants easy money (242).
Links: 2:229 = 5:82; 2:234 = 5:88, 91; 2:241 = 5:94; 2:242 = 3:271; 3:59 (Cephala wants
Muramasa for Fontana); 2:230 (the "sword master" is left ambiguous; Alba, per 227, is a
candidate).

**2.29 Alba's past, a thread across 2.21-2.28.** Flagged 2 (open).
103, 204, 227, 169, 216, 231, 232, 228, 233, 180 read together: the bow boast, then
"better with a katana", a Ranger "at present", won't talk about it, the lapse that kills,
lost comrades, Rosea's concern, his worry for Fontana's young party. His diction is
samurai-drama. Payoff: 264-265, he is burned to ash at the small door (S47).
Links: 3:195 (Lilia thinks Alba is suave and mature).

**2.30 You told me that already (243-247, 253).** Not flagged.
Links: 2:246 = 5:97; 2:247 = 3:272; 2:253 = 3:262.

**2.31 Menu labels (248-252, 267-270).** Topics and services.

**2.32 Artemisia's talk lines (254-260).** Not flagged.
When: late game, after she joins (Roster N7-N9). Training Maze gear only some races and
classes can use (254); the lost spell she "winged", 'Likaton' (255); the Priest attack
spell she found (256); nothing new (257, 260); "I love hunting down lost magic" (258-259).
Links: 3:233, 239, 251, 253, 256 (her Fontana-party versions; 2:257-259 = 3:244, 232-233,
2:260 = 3:217); the lost-spell thread.

**2.33 Progress report: the frozen man (261).** Flagged 3 (open).
Where: Underground B3F, the man in the ice (S12, WT ch. 3). Balbo thinks it's a trap and
asks if there's a bridge. Links: S12, S15.

**2.34 Progress report: the green stone (262).** Flagged 3 (open).
Where: Area A B4F (S22, WT ch. 7). Isn't the green stone enough? Something's missing.

**2.35 Progress report: the giant face (263).** Flagged 3 (open).
Where: unknown. A statue of a giant face; they'll tell the scholars; "go on ahead and
examine the statue". Candidates: the coffin's face-like relief (S52), but Balbo still
trusts the scholars, which suggests before the reveal (WT "Not yet placed").

**2.36 Alba turned to ash (264-265).** Flagged 3 (open).
Where: Area D, the small door (S47, WT ch. 14). Alba went in and came out as ash; they
take him to the Temple. Named 264, unnamed 265.
Links: S21, S47 (the gold equipment); EV 225-226 (the same fate in the event script).

## NPC_MES3: Fontana's party

**3.1 Greetings (0-11).** Flagged 4 (0-18) and 7 (9, 11), open.
Young samurai 0-2 (2 "Are you the new search party?"), Big Dracon 3 (Zaril), Woman with
a spear 4, Green-haired elf 5, Little elf 6, Fontana 7-8. Reiran 9 and 11, and Faerie
with a katana 10: after the split, when she has joined them. 9 is her reunion speech:
she helped "these kids" as a part-time gig and her alignment changed.
Links: 3:3 = 5:0; 3:5 = 1:11; 3:10 = 2:15.

**3.2 Farewells (12-32).** Flagged 4 (12-18; open).
Unnamed 12-17, Fontana 18-21, Zaril 22-23, Artemisia 24-26, Lilia 27-28, Cephala 29-30,
Reiran 31-32. The dead-member variants are 19, 22, 24, 27, 29, 31.
Links: 3:13 = 5:5, 3:23 = 5:9 (Zaril), 3:22 vs 5:8.

**3.3 Greetings that react to your party (33-66).** Flagged 12 (open).
Zaril 33-38 (wants your splendid equipment 36; the sanctity of life 37, for a party with a
high kill count (Inferred); "Hey there, comrade" 38, trigger unknown); Artemisia 39-43; Lilia
44-50; Cephala 51-59 (gives a broke party 100 Gp 54, the meowing of your cat-people 55,
big brothers and sisters, items love you, the Muramasa for Fontana 59); Reiran 60-66.
Links: 3:33-38 ~ 5:20-25 (Zaril's versions); 3:39-43 = 2:67-71; 3:44-50 = 1:293-294,
73-77; 3:60-66 = 2:58-64.

**3.4 The STAFF statue (67-71).** Flagged 3 (open).
Where: Area X north-east, the statue with the white stone (S20, WT ch. 6). 67 unnamed
version: they forgot "that thing" and hurry back. 68-71: the statue has a slot for the
Tablet of the Sun; the glyphs are a key; Artemisia: the little tablet had the same glyphs.
Links: S19, S20; 2:84-85; 4:30-41; the TABLET OF THE SUN (once LITHOGRAPH OF SUN).

**3.5 The maze changes (72-73).** Not flagged.
After mimicry mode (S47): "Looks like we teleported into a new maze." Unnamed 72, named
73. Links: 1:98-103.

**3.6 The first-meeting speech (74).** Flagged 4 (open).
When: early (Inferred: Roster N10 is first met at Shrine 4F E11 N10). Searching for the
Priestess too, still green, no leads; let's trade information.

**3.7 Zaril walks out (75-89).** Flagged 1 (open).
Where: Area A B2F x6y11 (Walkthrough, WT ch. 8). 75 the unnamed version (Zaril says he's
quitting). 76-87 the quarrel: Artemisia has had it, "You're not fit to be leader", Zaril
leaves; Lilia agrees he'd do fine alone and suggests making Zaril leader; Artemisia's
"Well, take care!" and Cephala's "That's cold of you". 88-89 Fontana, embarrassed: the
party will split up for now.
Links: the Roster change (Who moves where); 1:207-210, 2:185-187, 3:197-200, 4:108-110;
5:27-28; S28.

**3.8 The pit in the rubbish room (90-108).** Flagged 11 (open).
Where: the TRASH room (S36), Area C (Inferred, WT ch. 12). 90-92 narration: the floor
sucks you down. Fontana's party is already there (93-96 named, 97-100 unnamed); a man's
voice lowers a rope. 101-102 it was Guy ("I owed you one... you really ought to take a
bath"); 103-107 or Balbo ("leave that rope where it is"); 108 later, the rope leads
down.
Links: S36; 1:80-85 (the debt).

**3.9 Introductions (109-123).** Flagged 8 (open).
Fontana is 13 and a born samurai (111); Zaril; Artemisia; Lilia; Cephala's full name and
"I'm still just a girl of 13" (115); Reiran (116, after the split). Repeats 117-123
(Lilia pretends to be hurt you forgot her, Cephala: "Is my name hard to remember?").
Links: 3:113 = 2:107, 3:114 = 1:123, 3:116 = 2:105; 3:228 (Cephala: do you remember my
full name?).

**3.10 Healing (124-144, 279).** Flagged 13 (132; open).
Artemisia 124-131, Cephala 132-144 (139: revival magic and Mahaman are the spells she's
never sure of; 143 "You owe me one").

**3.11 Identify (145-150, 280).** Not flagged.
Cephala; 148 a failure, "It won't come off."

**3.12 Recovering your dead (151-154, 281).** Not flagged.
Fontana offers to take a wiped-out party back; 154 "Are you a professional rescue
squad?"

**3.13 Selling an unidentified item (155-162).** Not flagged.

**3.14 A practice fight (163-165).** Not flagged.
Fontana thinks you're joking; "I've already drawn my sword!"

**3.15 Talk: news, told them, about themselves (166-180).** Not flagged.
News nothing 166-170; told-them reactions 171-175; about themselves, refused 176-180
(Fontana "nothing interesting about me", Zaril "Why should I tell you?", Lilia
"Naughty").
Links: 3:167 = 5:54; 3:172 = 5:57, 60; 3:174 = 1:194; 3:169 = 1:181.

**3.16 Other parties: Guy (181-189).** Not flagged; Open question on 186.
A man called Guy who kept saying he was a hero; Zaril: some Lord spouting about being a
hero; Lilia: hot-blooded, stifling; Cephala: "You'd think a man his age would know
better." 186 Lilia calls him ガイルディア (a slip, or her not bothering with his name).

**3.17 Other parties: Balbo (190-196).** Flagged 6 (194; open).
Fontana found them scary; Zaril's first Evil Lord (192, = 5:63); Artemisia: Kiku was
scared, but Balbo didn't seem bad (193); 194 Fontana's real name is Kikunoshin; Lilia
prefers Alba; Cephala can't tell whether an Evil Lord is a good person.

**3.18 Other parties: Zaril (197-200).** Flagged 10 (197; open).
After the split: Fontana's quiet "Zaril... has formed a party of his own"; Artemisia: he's
just the same; Cephala: he wanted to be leader, "Grown-ups are so complicated."
Links: 1:207-210.

**3.19 Other parties: the scholars (201-206).** Not flagged.
Fontana: very kind; Zaril: saw them in the archives (= 5:67); Artemisia: "old scholar
guy... Cleo?"; Lilia liked the elf (204) but not the gnome, a sourpuss, nor the human,
who was scared of something (205); Cephala: Cleo studies the Shrine more than he
searches for the Priestess (206).
Links: 4:111-113, 143 (Cresson's fear), 4:121-123.

**3.20 Other parties: the stranger (207-214).** Not flagged.
Fontana: he glared at us; Zaril: garb like nothing he's ever seen, "something nasty"
(209-210 = 5:70-71); Lilia: killing intent (= 1:223); Cephala: a suspicious grown-up who
snorted at them.
Links: the shadow thread.

**3.21 Talk: news, nothing (215-219, 242-246).** Not flagged.

**3.22 Talk: personal and about themselves (220-241, 247-259).** Flagged 5 (257-258,
done), 6 (220-221, 229-230, 247-248, 255), 8 (236), 9 (231, 249-250), 10 (237), open.
Kikunoshin (220-221, 229-230: please call me Kikunoshin, "Heh... I knew it"; 247-248 he
changed his name and it changed back; 255 Zaril heard he wants to); Zaril can handle
sword and magic (222); Artemisia, Kiku and Cephala are childhood friends (223-226); Lilia
is the oldest (227); Cephala: do you remember my full name? (228); Zaril likes Balbo
(231) and picks fights to turn Evil (249-250); Artemisia loves lost magic (232-233) and
found a Priest attack spell (239); Lilia: stay out of her experiments (240); Cephala can
use any magic but can't carry heavy gear, being a Bishop "or rather, a young girl"
(236); Fontana: a sword is all he's good for (237); Zaril: you're greenhorns too (238);
Artemisia on Training Maze gear (251); Lilia: do people eat monsters? (252); Cephala:
the revived spell only lowers the caster's AC by 2 (253); Fontana: we won't lose to you
(254); Artemisia: 'Likaton' (256); Lilia wants you to scout her (257-258); Cephala was
born with such strong magic she had to be wrapped in a sealing cloth (259).
Links: 5:86, 89-90; 2:254-256, 258-259; 1:258 (Linaria and monster-eating); 1:266-267.

**3.23 You told me that already (260-264).** Not flagged.

**3.24 Reiran's talk lines (265-272).** Not flagged.
After the split. Her NPC_MES2 lines (= 2:160, 166, 172, 214, 207, 225, 242, 247).

**3.25 Menu labels (273-277, 279-282).**

**3.26 Fontana's god-word hint (278).** Flagged 2 (open).
Where: Area D, the altar that asks for the god's name (S45, WT ch. 14). Do you know a
word for a god? "I'm sure it isn't the god Kadorto." He'll ask the Fortune Teller.
Links: S45; 1:289; SISETU 341; the DIMGUIL thread.

## NPC_MES4: the scholars

**4.1 Greetings and farewells (0-8, 152-155).** Flagged 8 (open).
Robed elf (Cleo) 0-1 ("Welcome to the underground archive"), Cleo 2-4, farewells 5-8.
152-155 Cresson's greeting and farewell, unnamed and named: when he is alone (Inferred:
after the control room, when Cleo and Bergamot are gone).
Where: the library, Underground B3F x8y6 (WT ch. 3; S11).

**4.2 Greetings that react to your party (9-21).** Flagged 7 (open).
Bergamot 9-13 (your vintage; a party that can cast everything; "just muddle along" with
the glyphs, which he can't read himself, 11; "Marguda and Arabik", a name easter egg of
unknown source, 12; remarkable power that may open the sealed door, 13). Cresson 14-21
(a character named after "so dreadful a god" should change name 14; vitality fit for a
monster, watch out for Labadi 15; join us, "Only joking" 16; try changing class 17;
boys, girls, ご同輩 18-20; a primer 21).
Links: 4:13 and 4:25-27 (the Opener of the Door); 4:14 and the DIMGUIL thread; 4:11 vs
4:50, 127 (Bergamot laid out the glyphs he says he can't read).

**4.3 Cleo after the maze changes (22-23, 42-43).** Flagged 6 (open).
After mimicry mode (S47, WT ch. 15). 22-23: "Just as I'd predicted", no wizard's maze,
"Would you mind going home?" 42-43: a wealth of research material, he must report to
the King.
Links: S47, S51; SISETU 326 (not of this world); 5:108.

**4.4 Cresson's epilogue (24-29).** Flagged 2 (open).
When: after the control room (Game: "those two won't be coming back"); the first visit
is likely after the ending (WT ch. 19). He was a captive, not a heretic; some heretics
awaited the Opener of the Door; Cleo and Bergamot could not become it; you became it;
tell the world, and he'll wait for the next Opener.
Links: S52, S53 (the Priestess waits "for those who seek more"); 4:111-113, 116, 119-120,
125, 140, 143 (his earlier hints); 5:105.

**4.5 The tablet at the central computer (30-41).** Flagged 6 (open).
Where: Area X, the 26-letter pedestal (S19, WT ch. 6). Named 30-35, unnamed 36-41: a
small stone tablet with all 26 glyphs; Cresson calls it a switch; they'll continue in
the library.
Links: S19; 2:84-85; 3:67-71.

**4.6 The control room (44-55).** Flagged 1 (open).
Where: Area E B4F, through the BRIDGE door (S51, WT ch. 17). 44 the black shadow again
("by now the shadow was a familiar sight"), but something different comes out; Cleo
welcomes you, and "after I warned you so very firmly not to go any further" (46);
Bergamot's voice: no business helping the likes of them (48); Cleo: we took your
Priestess, hid the monsters at the altar and laid out the glyphs, as our god desired
(50); Bergamot: the god's command, fight whoever appears before this door (51), and the
heretics brought people in, helped them and set traps to drive them off (52); Cleo: the
heretics waited generations for the Opener of the Door (53); "Us, or you" (54). 55 the
shadow again: "you who know nothing... Have at you!" (the fight, Roster N15).
Links: 5:103-106 (44 and 55 open with the same narration as 5:103, and Cleo's 忠告 in
46 is the shadow's word in 5:105-106); 1:86-88; EV 130 and the planted hints; S53.

**4.7 Introductions (56-63, 166).** Flagged 8 (open).
Cleo: lately many self-styled adventurers drop by (56), Cleodendrum, "a Bishop, believe
it or not" (57); Bergamot (58); Cresson (59). Repeats 60-63 (62 Bergamot: memories like
sieves; flagged 4).

**4.8 Healing (64-77, 163).** Flagged 10 (open); 72 also flagged 4.
Cleo 64-70 ("a valuable source of information to us", 64); Bergamot 71-77 ("Makin' sport
of an old man", 72). From Area X on, they're always out of magic (Walkthrough).
Links: 4:64 reads differently after the reveal.

**4.9 Identify (78-83, 164).** Flagged 10 (open).
Cleo; 81 a failure curses it.

**4.10 The glyph check (84-85, 161-162).** Not flagged.
161-162 Cresson gives you the analysis item (use it in camp), on the second visit
(Walkthrough). 84-85 he compares your decoding with theirs; 100% "proves our research
was right".
Links: the ancient-glyph thread in event-map; 4:11, 127.

**4.11 Talk: news and told them (86-94).** Not flagged.
Nothing to tell (86-88; Cresson "P-please stop. I don't know anything"); reactions
(89-91); nothing (92-94; Cresson "I'm only the assistant").

**4.12 Other parties: Guy (95-99), Balbo (100-104), Fontana (105-107), Zaril (108-110).**
Flagged 9 (open).
Guy "a rather peculiar fellow"; Balbo "a coarse feller" Cresson doesn't do well with;
Fontana's party "full of beans", Bergamot can't stand children and Cleo let them run
wild; Zaril now leads his own party (after the quarrel, WT ch. 9).
Links: 1:211-217, 2:188-194, 3:201-206 (how the others saw the scholars).

**4.13 Cresson's frightening person (111-113).** Flagged 5 (open).
Topic: other parties (Inferred from position, where the other files have their
stranger block). Cleo: young Cresson met a very frightening person deep in the Shrine;
Bergamot: a heretic-looking man; Cresson: "I never met any heretics."
Links: the shadow thread; 3:205 (Lilia: the human was scared of something).

**4.14 Talk: news and told them (114-120).** Flagged 5 (116, 119-120; open).
Nothing new (114-116; Cresson begs not to be asked); reactions (117-120; Cresson starts
to say something and stops: "Really... it's... nothing.").

**4.15 Talk: about themselves (121-128).** Flagged 4 (124) and 5 (125), open.
Cleo: they came to rescue the Priestess too, then found this room, and scholars are
greedy for knowledge (121-123); Bergamot is hard of hearing (124); Cresson: beware the
altars, some are dangerous (125); their fields: monsters, ancient writing and magic
circles, architecture (126-128).
Links: 4:50 (the altars were theirs); S7.

**4.16 Talk: news (129-133).** Not flagged.
Nothing (129-131); Cleo: monsters band together in parties too, fascinating (132-133).

**4.17 The tea cakes (134-139).** Flagged 3 (open).
Topic: news (Inferred). Bergamot brought back tea cakes from the castle and can't find
them; Cresson: "You ate them yesterday, with Cleo."
Links: 4:143 (where do they really go when they go up for supplies?).

**4.18 Cresson's warnings and the Training Maze (140-143).** Flagged 5 (140, 143; open).
Cresson: be careful of the heretics (140); Cleo would love to see the Training Maze's
monsters (141); Bergamot: it has codes like the Shrine's (142); Cresson: Cleo and
Bergamot go up for supplies, "but... where do they really go" (143).
Links: S55; 2:238, 254, 3:251.

**4.19 Ask the others; told me already (144-149).** Flagged 4 (148; open).

**4.20 Cresson's history of Ganess (150-151).** Flagged 11 (open).
The tyrant Ganess II, cursed to death by the Shrine's shamans; his son, who sold the
lake's magic water and honors the native customs; "Could the troubles we face now have
something to do with the past?"
Links: S13 (the lake), SISETU 327; EV 210-211.

**4.21 Menu labels (156-160, 163-166).**

## NPC_MES5: Zaril's party, the shadow, the mysterious man, Agan

**5.1 Unnamed greetings and farewells (0-7).** Flagged 1 (open).
Big Dracon (Zaril) 0-1, 5; Shaggy man (Gaura) 3, 6; Short man (Fritillaria) 4, 7.
Zaril 2 "Long time no see" (a player who knew him in Fontana's party, Inferred).

**5.2 Farewells (8-12).** Flagged 8 (open).
Zaril 8-9, Gaura 10-11 ({ff12} "wasn't moving"), Fritillaria 12.

**5.3 Greetings, including reactions to your party (13-25, 113).** Flagged 3 (open).
Fritillaria 13-17 (murder squad 16, walking corpse 17), Gaura 18-19, Zaril 20-25 (your
equipment 23, the sanctity of life 24, comrade 25). 113 Zaril "Long time no see"
(= 2).
Links: 1:78-79 = 5:16-17; 3:33-38.

**5.4 Introductions (26-34, 117, 122-123).** Flagged 2 (open).
26 Big Dracon; 27 "I am Zaril, leader of this party", or 28 "starting now I'm gonna be
the leader" for a player who knew him in Fontana's party; "this little one's
Fritillaria" ("Ya didn't have to say 'little'!"), Gaura "Yo!"; "Friendly-like, if we can
manage it." 122-123 alternates.
When: after the Area B rescue (Roster N14; WT ch. 9).

**5.5 Healing (35-42, 114).** Flagged 4 (open).
Zaril, grudging ("quit wasting my time").

**5.6 Selling an unidentified item (43-50).** Not flagged.
"No Bishop in our party, see."

**5.7 The fight challenge (51-53).** Flagged 5 (open).
Zaril argues with taunts you never say on screen and talks himself into a duel; if you
back out, "So you're the chicken, then."

**5.8 Talk (54-97).** Flagged 6 (54-76) and 7 (63, 84, 86, 89, 90), open.
- News, nothing (54-56); told them (57-62).
- Other parties: Balbo (63-66: Zaril's first Evil Lord, Fritillaria won't like him
  because he calls him a brat, Gaura ran away from him); the scholars (67-69,
  Fritillaria: the elf is real nice); the stranger (70-73: Zaril's strange garb;
  Fritillaria met a busy Fighter- or Lord-like man, long before Zaril, "maybe he ain't
  from this world?", possibly Agan, 72; Gaura: scary man).
- News, nothing (74-76); about themselves (77-79: Fritillaria wants to be a Ninja, a
  change from his Guy-party line 1:240).
- Told them (80-82); nothing, and Fritillaria's loyalty (83-85: paralyzed and ditched,
  Zaril saved him).
- Personal (86-91): Zaril thinks Balbo's all right and picks fights to turn Evil;
  Fritillaria likes Zaril as he is; Gaura will be a Samurai.
- Refusal, reaction, Muramasa (92-94); told me already (95-97).
Links: 3:192, 202, 209-210, 216, 222, 231, 238, 243, 249-250 (Zaril's Fontana-party
copies); 2:192, 199, 206, 213, 224, 229, 234, 241, 246 (Gaura's Balbo-party copies);
1:240 vs 78.

**5.9 Menu labels (98-102, 114-117).**

**5.10 The shadow's warning (103-106).** Flagged 9 (open).
Where: Area B B2F x17y10, behind the north door (Walkthrough, WT ch. 10). 103 the black
shadow seeps out; 105 the Mysterious figure: "Begone, unbelievers in the old god!",
beyond is the holy ground of the Opener of the Door, heed my warning (忠告); 104 it
melts away. 106 the Mysterious man later, if you go on: "You have scorned my warning!"
(where isn't known).
Who: not named. **Inferred** that it is Cleo or the heretics: the control room opens
with the same narration and "by now the shadow was a familiar sight" (4:44), and Cleo
says he warned you firmly (4:46, 忠告). harano guessed Cresson (event map).
Links: 4:44-55; 1:218-223, 2:195-202 (2:200 "Begone!"), 3:207-214, 4:111-113; S43.

**5.11 The mysterious man's warning (107).** Not flagged.
Where: unknown. "Beyond this point lies the real world"; turn back if it's dreams you
seek; you aren't ready. **Inferred:** a separate speech for a party that arrives at Area
Z too soon or by the golem route (event map S52).

**5.12 The mysterious man in Area Z (108-111).** Not flagged.
Where: Area Z, on entering the great hall at x10y6 (Inferred, WT ch. 18; S52). The
Shrine is a great iron ship; a fatal accident left him alone; his experiments crumbled
out of the tanks or hatched and never grew; the ship's leaking fuel produced you,
"lesser beings"; he crossed "our father" with a creature of this world; "Face my
father, who is also myself."
Links: S29, S30, S48 (tanks, eggs, failed growth); S52; 4:22, 42 (no wizard's maze);
SISETU 326.

**5.13 Agan (112).** Flagged 10 (open).
Where: unknown (WT "Not yet placed"). "I am Agan, the eternal traveler", carried into the
past by demons, seeking a sealed place below where monsters stir that even the gods
can't control (the Dragon's Cave, S56).
Links: S56, S57 (Otaka: "not a word to Agan!"); 5:72.

**5.14 Zaril's party rescued (118-121).** Not flagged.
Where: Area B B3F x12y11, beside the LABORATORY door, after the Chimera Warrior (S28,
WT ch. 9). Gaura groans, Zaril yells, Fritillaria cries for help, and a party suddenly
appears (121).
Links: S28 (EV 150-152, 194), S30 (the experiment log); Catalog 12:27.

## Threads across the files

**Searching for the Priestess.** Every party says it's looking for her at first meeting:
1:0-6, 2:72, 3:2, 3:74, and the scholars came for her too (4:121). Guy, after the
ending, hasn't heard she came back (1:279). Cleo took her (4:50). S53.

**The quarrel and the member swap.** 3:75-89 is the event; the gossip is 1:207-210,
2:185-187, 3:197-200, 4:108-110; the consequences are the Roster changes (Who moves
where) and Zaril's party in Area B (S28, 5:118-121). Lilia's "scout me" lines (1:266,
3:257) set up her move to Guy.

**Guy the hero.** 1:1, 86-88, 115, 124, 128, 202, 248, 295; others on him: 2:174-178,
3:181-189, 4:95-99 (and Balbo's "champion of justice"). Keep "hero" everywhere, "Hero"
where it's a class (npc-translation).

**Alignment flips.** Guy (1:94-97), Balbo (2:92-93, 203), Reiran (3:9), Zaril wanting to
turn Evil (3:231, 249-250; 5:86, 89-90), Alstron once Evil (1:205). Party-alignment
greetings: 1:1, 1:13, 1:50, 2:1, 2:49, 2:75-78.

**Alba.** 2.29 above; 2:264-265 (ash); 3:195 (Lilia's crush).

**Kikunoshin.** 3:111, 193-194, 220-221, 224-226, 229-230, 247-248, 255. Zaril renamed
him after a hero from his homeland. Open question: "Kiku" or "Kiku-chan".

**The stranger, the shadow, and the heretics.** Every party has met someone frightening
(1:218-223, 2:195-202, 3:207-214, 5:70-73), and Cresson won't talk about the man he met
(4:111-113, 116, 119-120). The shadow warns you off (5:103-106); Cresson warns about
altars and heretics and wonders where his colleagues really go (4:125, 140, 143); the
payoff is the control room (4:44-55), which reuses the shadow's narration and word for
"warning". Fritillaria's man "not from this world" (5:72) is more likely Agan. Keep the
shadow's narration identical in 4:44, 4:55 and 5:103, and keep 忠告 as "warning" in
4:46, 5:105, 5:106.

**The scholars as others see them.** 1:211-217, 2:188-194, 3:201-206, 5:67-69. Lychee
(1:214) and Artemisia (2:194, 3:203) call Cleo old; he's an elf. Lilia likes him (1:216, 3:204);
Balbo says they won't tell you anything (2:189), which reads differently after 4:50.

**The maze changes.** 1:98-103, 2:90-91, 3:72-73, 4:22-23, 4:42-43; S47.

**Puzzle hints.** 1:286-289, 2:82-89, 2:261-263, 3:67-71, 3:278, 4:84-85, 4:125. Two
send you to the Fortune Teller (1:287, 3:278).

**Lost spells.** Artemisia (2:255-256, 3:239, 3:256, 'Likaton'), Lilia's warning (3:240),
Cephala's verdict (3:253: AC -2, "lost for a reason").

**The Training Maze.** 2:238, 2:254, 3:251, 4:141-142; S55.

**Eating monsters.** Linaria (1:249, 1:258), Lilia (3:252).

**Muramasa.** Gaura wants it (2:241, 5:94); Cephala wants yours for Fontana (3:59).

**Felpurr.** Rosea is half Felpurr (2:205, 239-240) and tagged "cat-eared woman"; Cephala
notices your meowing cat-people (3:55).

**Tavern joke names.** 'A' (1:60), 'Mule' (1:68), 'Richguy' (1:75, 3:48), 'Appraiser'
(2:50), and the too-embarrassing name (1:72, 2:56).

**Cards.** Alstron found a "card" (1:259); Reiran: the Card Master's complete set (2:60,
3:62).

**Ages.** Fontana and Cephala are 13 (3:111, 115), Lilia "seventeen and holding" and the
oldest of hers (1:241, 3:227), Reiran 18 (2:207). Old-party greetings: 1:70-71, 76-77,
2:63, 3:49-50.

**Services.** Healing, identify, body recovery, item sale and practice fight exist in
every party file with each party's own spin; the A-D item menu is shared (1:170, 2:149,
3:158, 5:46).

## Could not be placed in time

The scene each of these belongs to is clear; when or where it plays isn't.

- 1:89-93, 296: Guy resting outside a trap room.
- 1:94-97: Guy goes Evil and back.
- 1:15: an Artemisia line in Guy's file (probably unused).
- 1:303: the party vanishes, leaving money.
- 2:92-93: Balbo's alignment flips.
- 2:263: the giant face statue.
- 5:106: the shadow's second warning.
- 5:107: the mysterious man's "real world" warning.
- 5:112: Agan.
- Roster N6 and N11: the stage they cover.
- Every talk-menu line: which of a topic's several blocks plays at a given visit is not
  decoded; the stage-specific ones are placed only where their content dates them.

## Checking coverage

The headings above are the coverage record: every "(a-b, c, ...)" in a heading under a
file's section counts as placed. Regenerate the check with:

```
python3 - <<'EOF'
import re
doc = open('docs/npc-map.md').read()
sizes = {1: 304, 2: 272, 3: 283, 4: 167, 5: 124}
parts = re.split(r'^## NPC_MES(\d)', doc, flags=re.M)
for i in range(1, len(parts), 2):
    n, body = int(parts[i]), parts[i + 1].split('\n## ')[0]
    seen = set()
    for h in re.findall(r'^\*\*\d+\.\d+ [^*]*\*\*', body, flags=re.M):
        for grp in re.findall(r'\(([^)]*)\)', h):
            for a, b in re.findall(r'(\d+)(?:-(\d+))?', grp):
                seen.update(range(int(a), int(b or a) + 1))
    missing = sorted(set(range(sizes[n])) - seen)
    print(f'NPC_MES{n}: {len(seen & set(range(sizes[n])))}/{sizes[n]}, missing {missing}')
EOF
```
