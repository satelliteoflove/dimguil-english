# Play-through review plan: paused NPC lines by chapter

Chris plays through with the monitor pausing on every NPC line that is `open`, `ai-reviewed`
or `check` (`scripts/textstatus.py`). There are 750 such lines. This plan puts them in
play order so a chapter or two can be reviewed ahead of where he is. Chapters follow the
walkthrough's numbering and the bot's order: 1 to 17, then 19 (the ring for the
Priestess's Door), then 18 (Area Z and the ending). Chapters 1, 11, 13 and 16 have none placed. Machine-readable version: `rips/playplan/npc-by-chapter.json`; the scripts that
built it are `scripts/playplan/build_plan.py` and `write_md.py`.

## How much is evidence

241 of the 750 lines are placed in a chapter and 509 are not.
Of the placed lines, 134 were seen on screen by a bot run in that chapter (of which
29 come from older multi-chapter runs, marked `*`, and sit at the earliest chapter the run
covered), 97 come from the site walkthrough's NPC placements
(`docs/walkthrough-npcs.json`), and 10 from a chapter named in `docs/npc-map.md`.
Nothing is placed by guesswork alone (0 inferred), but the walkthrough
and map placements are sources' claims, not seen in play. Where the bot and the walkthrough
disagree the earlier chapter wins, since an early review is harmless.

The bot only reaches a handful of NPC lines per chapter, because it rarely talks to them.
That is why most paused lines are unplaced: they are talk-menu, healing, identify, shop
and greeting-variant lines that play whenever a party is met and a topic is chosen, and
the code that picks them is not decoded. They are listed by party at the end with the
first chapter the party can be met. The placed lines are the scenes that trigger on a
place or event, plus whatever greetings the bots happened to hit.

## Chapter by chapter, in play order

Lines are `n:k`, NPC_MESn string k, as in `docs/npc-map.md`. Open scene is `n/scene number title (priority)` from `docs/npc-review.md`; "ai-reviewed" means no scene is open for the line, but Chris hasn't seen it. Evidence is bot, walkthrough or map (`*` = from a multi-chapter run).

### Chapter 1: The four pillars

No paused NPC lines placed here.

### Chapter 2: The Shrine and the jade mask

33 paused lines, 2 of them in open scenes. Balbo's party 31; Fontana's party 2.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Balbo's party | 2.13 Introductions | 2:96,98-100 | 4 | ai-reviewed | bot* 4 |
| Balbo's party | 2.2 Farewells | 2:21,23,25 | 3 | ai-reviewed | bot 2, bot* 1 |
| Balbo's party | 2.20 Talk: told them | 2:215,217-220 | 5 | ai-reviewed | bot* 5 |
| Balbo's party | 2.22 Other parties: Guy | 2:174-178 | 5 | ai-reviewed | bot* 5 |
| Balbo's party | 2.23 Other parties: Fontana | 2:179,181-184 | 5 | ai-reviewed | bot* 5 |
| Balbo's party | 2.28 Talk: personal | 2:226,229-230,236-237 | 5 | ai-reviewed | bot* 5 |
| Balbo's party | 2.31 Menu labels | 2:249,251-252,270 | 4 | ai-reviewed | bot* 4 |
| Fontana's party | 3.2 Farewells | 3:12 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Fontana's party | 3.6 The first-meeting speech | 3:74 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |

### Chapter 3: The Underground Shrine and the blue stone

35 paused lines, 33 of them in open scenes. Cleo's group (the scholars) 30; Fontana's party 5.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:1,4-5 | 3 | 3/4 First meeting and goodbyes (MEDIUM) | bot 3 |
| Fontana's party | 3.2 Farewells | 3:14-15 | 2 | 3/4 First meeting and goodbyes (MEDIUM) | bot 2 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:0-1,3,5-6,8,152-155 | 10 | 4/8 Introductions and repeat greetings (LOW) | walkthrough 2, map 8 |
| Cleo's group (the scholars) | 4.10 The glyph check | 4:161-162 | 2 | ai-reviewed | walkthrough 2 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:56-59 | 4 | 4/8 Introductions and repeat greetings (LOW) | walkthrough 4 |
| Cleo's group (the scholars) | 4.8 Healing | 4:64-77 | 14 | 4/10 Healing and identify (LOW) | walkthrough 14 |

### Chapter 4: The lake machine

14 paused lines, 3 of them in open scenes. Cleo's group (the scholars) 12; Fontana's party 2.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:3 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:13 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:7 | 1 | 4/8 Introductions and repeat greetings (LOW) | bot 1 |
| Cleo's group (the scholars) | 4.10 The glyph check | 4:84 | 1 | ai-reviewed | bot 1 |
| Cleo's group (the scholars) | 4.11 Talk: news and told them | 4:92-94 | 3 | ai-reviewed | bot 3 |
| Cleo's group (the scholars) | 4.16 Talk: news | 4:129-131 | 3 | ai-reviewed | bot 3 |
| Cleo's group (the scholars) | 4.21 Menu labels | 4:156,158 | 2 | ai-reviewed | bot 2 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:166 | 1 | ai-reviewed | bot 1 |
| Cleo's group (the scholars) | 4.8 Healing | 4:163 | 1 | ai-reviewed | bot 1 |

### Chapter 5: The moon door and the 2-Head Snake

1 paused lines, 0 of them in open scenes. Balbo's party 1.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Balbo's party | 2.2 Farewells | 2:24 | 1 | ai-reviewed | bot 1 |

### Chapter 6: Area X and the white stone

17 paused lines, 17 of them in open scenes. Cleo's group (the scholars) 12; Fontana's party 5.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.4 The STAFF statue | 3:67-71 | 5 | 3/3 The Sun statue (HIGH-MEDIUM) | bot 1, walkthrough 4 |
| Cleo's group (the scholars) | 4.5 The tablet at the central computer | 4:30-41 | 12 | 4/6 The research scenes and the tablet (MEDIUM) | bot 12 |

### Chapter 7: Area A: the green stone

16 paused lines, 15 of them in open scenes. Cleo's group (the scholars) 16.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:4 | 1 | 4/8 Introductions and repeat greetings (LOW) | bot 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:95-107 | 13 | 4/9 Gossip about the other parties (LOW) | bot 13 |
| Cleo's group (the scholars) | 4.2 Greetings that react to your party | 4:11 | 1 | 4/7 Reactions to the player's party (MEDIUM) | bot 1 |
| Cleo's group (the scholars) | 4.21 Menu labels | 4:159 | 1 | ai-reviewed | bot 1 |

### Chapter 8: Area A: the yellow stone and the Jail Ogre

18 paused lines, 15 of them in open scenes. Fontana's party 15; Balbo's party 3.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Balbo's party | 2.24 Other parties: Zaril's split | 2:185-187 | 3 | ai-reviewed | walkthrough 3 |
| Fontana's party | 3.7 Zaril walks out | 3:75-89 | 15 | 3/1 Zaril walks out (HIGH) | bot 1, walkthrough 14 |

### Chapter 9: Area B: the black stone

30 paused lines, 22 of them in open scenes. Zaril's party 16; Fontana's party 9; Cleo's group (the scholars) 4; Balbo's party 1.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Balbo's party | 2.2 Farewells | 2:26 | 1 | ai-reviewed | bot 1 |
| Fontana's party | 3.1 Greetings | 3:2,6 | 2 | 3/4 First meeting and goodbyes (MEDIUM) | bot 2 |
| Fontana's party | 3.1 Greetings | 3:9,11 | 2 | 3/7 Reiran's reunion (MEDIUM) | walkthrough 2 |
| Fontana's party | 3.18 Other parties: Zaril | 3:197 | 1 | 3/10 Fontana's quieter lines (LOW) | walkthrough 1 |
| Fontana's party | 3.18 Other parties: Zaril | 3:198-200 | 3 | ai-reviewed | walkthrough 3 |
| Fontana's party | 3.2 Farewells | 3:16 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:108-110 | 3 | 4/9 Gossip about the other parties (LOW) | walkthrough 3 |
| Cleo's group (the scholars) | 4.2 Greetings that react to your party | 4:20 | 1 | 4/7 Reactions to the player's party (MEDIUM) | bot 1 |
| Zaril's party | 5.14 Zaril's party rescued | 5:118-121 | 4 | ai-reviewed | bot 3, walkthrough 1 |
| Zaril's party | 5.4 Introductions | 5:26-34,117,122-123 | 12 | 5/2 Introductions (HIGH) | walkthrough 10, map 2 |

### Chapter 10: Area B: the red stone

9 paused lines, 7 of them in open scenes. Fontana's party 4; The shadow 3; Zaril's party 2.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:8 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:21,32 | 2 | ai-reviewed | bot 2 |
| Fontana's party | 3.3 Greetings that react to your party | 3:60 | 1 | 3/12 Party-composition quips (LOW) | bot 1 |
| Zaril's party | 5.1 Unnamed greetings and farewells | 5:1,5 | 2 | 5/1 First sighting (LOW) | bot 2 |
| The shadow | 5.10 The shadow's warning | 5:103-105 | 3 | 5/9 The shadow's warning (MEDIUM) | bot 3 |

### Chapter 11: Area A: the gold armor

No paused NPC lines placed here.

### Chapter 12: Area C: the silver stone

19 paused lines, 19 of them in open scenes. Fontana's party 19.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.8 The pit in the rubbish room | 3:90-108 | 19 | 3/11 The pit trap (LOW) | walkthrough 19 |

### Chapter 13: Area C: the moving floors

No paused NPC lines placed here.

### Chapter 14: Area D: mimicry mode released

13 paused lines, 9 of them in open scenes. Fontana's party 7; Cleo's group (the scholars) 5; The shadow 1.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:7 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:18 | 1 | 3/4 First meeting and goodbyes (MEDIUM) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:19-20 | 2 | ai-reviewed | bot 2 |
| Fontana's party | 3.26 Fontana's god-word hint | 3:278 | 1 | 3/2 Fontana's god-word hint (HIGH) | walkthrough 1 |
| Fontana's party | 3.5 The maze changes | 3:72-73 | 2 | ai-reviewed | walkthrough 2 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:2 | 1 | 4/8 Introductions and repeat greetings (LOW) | bot 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:60-63 | 4 | 4/8 Introductions and repeat greetings (LOW) | bot 4 |
| The shadow | 5.10 The shadow's warning | 5:106 | 1 | 5/9 The shadow's warning (MEDIUM) | bot 1 |

### Chapter 15: Area C: the demon statue

6 paused lines, 4 of them in open scenes. Cleo's group (the scholars) 4; Balbo's party 2.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Balbo's party | 2.10 The maze changes | 2:90-91 | 2 | ai-reviewed | bot 1, walkthrough 1 |
| Cleo's group (the scholars) | 4.3 Cleo after the maze changes | 4:22-23,42-43 | 4 | 4/6 The research scenes and the tablet (MEDIUM) | walkthrough 4 |

### Chapter 16: Area A: the gold stone

No paused NPC lines placed here.

### Chapter 17: Area E: the control room

17 paused lines, 14 of them in open scenes. Cleo's group (the scholars) 12; Fontana's party 4; The mysterious man 1.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.2 Farewells | 3:30 | 1 | ai-reviewed | bot 1 |
| Fontana's party | 3.3 Greetings that react to your party | 3:52-53,61 | 3 | 3/12 Party-composition quips (LOW) | bot 3 |
| Cleo's group (the scholars) | 4.6 The control room | 4:44-54 | 11 | 4/1 The reveal in the control room (HIGH) | walkthrough 1, bot 10 |
| Cleo's group (the scholars) | 4.6 The control room | 4:55 | 1 | ai-reviewed | bot 1 |
| The mysterious man | 5.11 The mysterious man's warning | 5:107 | 1 | ai-reviewed | bot 1 |

### Chapter 19: The ring for the Priestess's Door (bot-only detour)

3 paused lines, 2 of them in open scenes. Fontana's party 2; Agan 1.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Fontana's party | 3.2 Farewells | 3:29 | 1 | ai-reviewed | bot 1 |
| Fontana's party | 3.3 Greetings that react to your party | 3:51 | 1 | 3/12 Party-composition quips (LOW) | bot 1 |
| Agan | 5.13 Agan | 5:112 | 1 | 5/10 Agan (LOW) | bot 1 |

### Chapter 18: Area Z and the ending (walkthrough 18-19)

10 paused lines, 6 of them in open scenes. Cleo's group (the scholars) 6; The mysterious man 4.

| Party | Scene | Lines (n:k) | Count | Open scene (priority) | Evidence |
|---|---|---|---|---|---|
| Cleo's group (the scholars) | 4.4 Cresson's epilogue | 4:24-29 | 6 | 4/2 Cresson's epilogue (HIGH) | walkthrough 6 |
| The mysterious man | 5.12 The mysterious man in Area Z | 5:108-111 | 4 | ai-reviewed | bot 4 |

## The HIGH-priority open scenes at a glance

| Scene | Priority | Placed lines by chapter | Unplaced lines |
|---|---|---|---|
| 3/3 The Sun statue | HIGH-MEDIUM | ch. 6: 5 | 0 |
| 3/1 Zaril walks out | HIGH | ch. 8: 15 | 0 |
| 5/2 Introductions | HIGH | ch. 9: 12 | 0 |
| 3/2 Fontana's god-word hint | HIGH | ch. 14: 1 | 0 |
| 4/1 The reveal in the control room | HIGH | ch. 17: 11 | 0 |
| 4/2 Cresson's epilogue | HIGH | ch. 18: 6 | 0 |
| 4/3 The tea cakes | HIGH | - | 6 |
| 5/5 The fight challenge | HIGH | - | 3 |
| 5/7 Zaril wants to turn Evil; Fritillaria's loyalty | HIGH | - | 4 |

## Things to know

- For 20 lines the bot first saw them in a later chapter than the walkthrough names, and those are placed by the walkthrough; the bot never saw one earlier than the walkthrough (0). Most are Cleo's group, who turn up as greetings and gossip in Areas A to D, well away from the library, so they roam.
- The two ending chapters are swapped in play order (19, then 18), as the bot plays them. Chapter 19 only adds three lines the bot met on the way (two Fontana's party greetings and Agan); the mysterious man in Area Z is placed in chapter 18, where the bot saw it as well.
- Three of the HIGH scenes are not tied to any chapter: the tea cakes (scholars), the fight challenge and the Fritillaria loyalty talk (Zaril's party). They are talk-menu topics, so they are met whenever the party is.
- Zaril's party is the biggest block of lines nobody can place: 96 lines, 69 of them open, from chapter 9 on.

## Not placed in a chapter (509 lines)

These have no chapter evidence. Grouped by party, then by the scene they sit in in `docs/npc-map.md`. "From" is the first chapter in which the party's file was seen or placed by the evidence above; the lines can turn up in any chapter after that when the party is met and a topic chosen.

### Event script (EV): 1 lines, 0 open

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Event script | Event script: which switch this is: "set into the wall" is wrong if it is the frog statue | EV:288 | 1 | check |

### Guy's party (1): 1 lines, 1 open, from chapter 1

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Guy's party | 1.5 Greetings that react to your party | 1:79 | 1 | open |

### Balbo's party (2): 144 lines, 0 open, from chapter 2

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Balbo's party | 2.11 Balbo's alignment flips | 2:203 | 1 | ai-reviewed |
| Balbo's party | 2.12 Lineup-change greetings | 2:94-95 | 2 | ai-reviewed |
| Balbo's party | 2.13 Introductions | 2:101-102,104-113,271 | 13 | ai-reviewed |
| Balbo's party | 2.14 Healing | 2:116-122,125-129,131-135 | 17 | ai-reviewed |
| Balbo's party | 2.15 Identify | 2:136-141,268 | 7 | ai-reviewed |
| Balbo's party | 2.17 Selling an unidentified item | 2:146-152,266 | 8 | ai-reviewed |
| Balbo's party | 2.18 A practice fight | 2:153-155 | 3 | ai-reviewed |
| Balbo's party | 2.19 Talk: news | 2:156-161,210-214,221-225 | 16 | ai-reviewed |
| Balbo's party | 2.2 Farewells | 2:27-32 | 6 | ai-reviewed |
| Balbo's party | 2.20 Talk: told them | 2:162-167 | 6 | ai-reviewed |
| Balbo's party | 2.21 Talk: about themselves, refused | 2:170-172 | 3 | ai-reviewed |
| Balbo's party | 2.25 Other parties: the scholars | 2:188-194 | 7 | ai-reviewed |
| Balbo's party | 2.26 Other parties: the stranger | 2:196-198,201-202 | 5 | ai-reviewed |
| Balbo's party | 2.27 Talk: about themselves | 2:205-209 | 5 | ai-reviewed |
| Balbo's party | 2.28 Talk: personal | 2:234-235,238-242 | 7 | ai-reviewed |
| Balbo's party | 2.30 You told me that already | 2:243-247,253 | 6 | ai-reviewed |
| Balbo's party | 2.31 Menu labels | 2:248,250 | 2 | ai-reviewed |
| Balbo's party | 2.32 Artemisia's talk lines | 2:254-260 | 7 | ai-reviewed |
| Balbo's party | 2.4 Greetings that react to your party | 2:47-50,52-69,71 | 23 | ai-reviewed |

### Fontana's party (3): 202 lines, 62 open, from chapter 2

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:0,10 | 2 | 3/4 First meeting and goodbyes (MEDIUM) |
| Fontana's party | 3.10 Healing | 3:124-131,133-144,279 | 21 | ai-reviewed |
| Fontana's party | 3.10 Healing | 3:132 | 1 | 3/13 Cephala's healing (LOW) |
| Fontana's party | 3.11 Identify | 3:145-150,280 | 7 | ai-reviewed |
| Fontana's party | 3.12 Recovering your dead | 3:151-154,281 | 5 | ai-reviewed |
| Fontana's party | 3.13 Selling an unidentified item | 3:155-162 | 8 | ai-reviewed |
| Fontana's party | 3.14 A practice fight | 3:163-165 | 3 | ai-reviewed |
| Fontana's party | 3.15 Talk: news, told them, about themselves | 3:166-180 | 15 | ai-reviewed |
| Fontana's party | 3.16 Other parties: Guy | 3:181-189 | 9 | ai-reviewed |
| Fontana's party | 3.17 Other parties: Balbo | 3:190-192,196 | 4 | ai-reviewed |
| Fontana's party | 3.17 Other parties: Balbo | 3:193-194 | 2 | 3/6 Kikunoshin, the name that won't st (MEDIUM) |
| Fontana's party | 3.19 Other parties: the scholars | 3:201-206 | 6 | ai-reviewed |
| Fontana's party | 3.2 Farewells | 3:17 | 1 | 3/4 First meeting and goodbyes (MEDIUM) |
| Fontana's party | 3.2 Farewells | 3:22-24,26-28,31 | 7 | ai-reviewed |
| Fontana's party | 3.20 Other parties: the stranger | 3:207-212,214 | 7 | ai-reviewed |
| Fontana's party | 3.21 Talk: news, nothing | 3:215-219,242-246 | 10 | ai-reviewed |
| Fontana's party | 3.22 Talk: personal and about themselves | 3:220-221,229-230,247-248,255 | 7 | 3/6 Kikunoshin, the name that won't st (MEDIUM) |
| Fontana's party | 3.22 Talk: personal and about themselves | 3:222-226,228,232-235,239-241,251-254,256,259 | 19 | ai-reviewed |
| Fontana's party | 3.22 Talk: personal and about themselves | 3:231,249-250 | 3 | 3/9 Zaril wants to be Evil (LOW) |
| Fontana's party | 3.22 Talk: personal and about themselves | 3:236 | 1 | 3/8 Introductions, Cephala's "little g (LOW-MEDIUM) |
| Fontana's party | 3.22 Talk: personal and about themselves | 3:237 | 1 | 3/10 Fontana's quieter lines (LOW) |
| Fontana's party | 3.23 You told me that already | 3:260-264 | 5 | ai-reviewed |
| Fontana's party | 3.24 Reiran's talk lines | 3:265-272 | 8 | ai-reviewed |
| Fontana's party | 3.25 Menu labels | 3:273-277,282 | 6 | ai-reviewed |
| Fontana's party | 3.3 Greetings that react to your party | 3:33-50,54-59,62-66 | 29 | 3/12 Party-composition quips (LOW) |
| Fontana's party | 3.9 Introductions | 3:109-123 | 15 | 3/8 Introductions, Cephala's "little g (LOW-MEDIUM) |

### Cleo's group (the scholars) (4): 66 lines, 36 open, from chapter 3

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Cleo's group (the scholars) | 4.10 The glyph check | 4:85 | 1 | ai-reviewed |
| Cleo's group (the scholars) | 4.11 Talk: news and told them | 4:86-91 | 6 | ai-reviewed |
| Cleo's group (the scholars) | 4.13 Cresson's frightening person | 4:111-113 | 3 | 4/5 Cresson's hints (MEDIUM) |
| Cleo's group (the scholars) | 4.14 Talk: news and told them | 4:114-115,117-118 | 4 | ai-reviewed |
| Cleo's group (the scholars) | 4.14 Talk: news and told them | 4:116,119-120 | 3 | 4/5 Cresson's hints (MEDIUM) |
| Cleo's group (the scholars) | 4.15 Talk: about themselves | 4:121-123,126-128 | 6 | ai-reviewed |
| Cleo's group (the scholars) | 4.15 Talk: about themselves | 4:124 | 1 | 4/4 Bergamot's "old coot" running gag (MEDIUM) |
| Cleo's group (the scholars) | 4.15 Talk: about themselves | 4:125 | 1 | 4/5 Cresson's hints (MEDIUM) |
| Cleo's group (the scholars) | 4.16 Talk: news | 4:132-133 | 2 | ai-reviewed |
| Cleo's group (the scholars) | 4.17 The tea cakes | 4:134-139 | 6 | 4/3 The tea cakes (HIGH) |
| Cleo's group (the scholars) | 4.18 Cresson's warnings and the Training Maze | 4:140,143 | 2 | 4/5 Cresson's hints (MEDIUM) |
| Cleo's group (the scholars) | 4.18 Cresson's warnings and the Training Maze | 4:141-142 | 2 | ai-reviewed |
| Cleo's group (the scholars) | 4.19 Ask the others; told me already | 4:144-147,149 | 5 | ai-reviewed |
| Cleo's group (the scholars) | 4.19 Ask the others; told me already | 4:148 | 1 | 4/4 Bergamot's "old coot" running gag (MEDIUM) |
| Cleo's group (the scholars) | 4.2 Greetings that react to your party | 4:9-10,12-19,21 | 11 | 4/7 Reactions to the player's party (MEDIUM) |
| Cleo's group (the scholars) | 4.20 Cresson's history of Ganess | 4:150-151 | 2 | 4/11 Cresson's history lecture (LOW) |
| Cleo's group (the scholars) | 4.21 Menu labels | 4:157,160,165 | 3 | ai-reviewed |
| Cleo's group (the scholars) | 4.9 Identify | 4:78-83 | 6 | 4/10 Healing and identify (LOW) |
| Cleo's group (the scholars) | 4.9 Identify | 4:164 | 1 | ai-reviewed |

### Zaril's party (5): 95 lines, 69 open, from chapter 9

| Party | Scene | Lines (n:k) | Count | Open scene (priority) |
|---|---|---|---|---|
| Zaril's party | 5.1 Unnamed greetings and farewells | 5:0,2-4,6-7 | 6 | 5/1 First sighting (LOW) |
| Zaril's party | 5.2 Farewells | 5:8-12 | 5 | 5/8 Farewells (MEDIUM) |
| Zaril's party | 5.3 Greetings, including reactions to your party | 5:13-25,113 | 14 | 5/3 Reputation greetings (MEDIUM) |
| Zaril's party | 5.5 Healing | 5:35-42,114 | 9 | 5/4 Healing (MEDIUM) |
| Zaril's party | 5.6 Selling an unidentified item | 5:43-50 | 8 | ai-reviewed |
| Zaril's party | 5.7 The fight challenge | 5:51-53 | 3 | 5/5 The fight challenge (HIGH) |
| Zaril's party | 5.8 Talk | 5:54-76 | 23 | 5/6 Talk: news, reactions, other parti (MEDIUM) |
| Zaril's party | 5.8 Talk | 5:77-79,81-83,85,87-88,91-97 | 16 | ai-reviewed |
| Zaril's party | 5.8 Talk | 5:84,86,89-90 | 4 | 5/7 Zaril wants to turn Evil; Fritilla (HIGH) |
| Zaril's party | 5.9 Menu labels | 5:98-102 | 5 | 5/6 Talk: news, reactions, other parti (MEDIUM) |
| Zaril's party | 5.9 Menu labels | 5:115-116 | 2 | ai-reviewed |
