# Play-through review plan: what to review before each chapter

Chris plays with the monitor (`scripts/playwatch.py`) pausing on every NPC line not yet
reviewed with him: lines in a review-tool scene still open, lines with a change proposed
there, and lines only the AI reviewers have read (`scripts/textstatus.py`). There are
412 such lines now, in 26 review-tool scenes. This plan
says which scenes to finish before each chapter, so the monitor rarely stops. Built by
`scripts/playplan/build_plan.py` and `write_md.py` from the review tool's scenes and
decisions; rerun both after a review session.

38 more lines are reviewed and committed but newer than the published disc; the
monitor pauses on those too ("behind") until the next build and publish, so build before
each session.

A scene's chapter is the first chapter where one of its lines is placed (seen by a bot
run there, or named by the site walkthrough or `docs/npc-map.md`), or, for talk-menu
lines nobody can place, the chapter where the party is first met. Chapters are in play
order: 1 to 17, then 19 (the ring for the Priestess's Door), then 18 (Area Z and the
ending).

## Scenes to finish, by chapter

### Before chapter 2: The Shrine and the jade mask

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| Cephala's voice: a prim little girl with a dry streak (part 1 of 3) (`voice-cephala-1`) | 3:6,16,29-30,51-59,79,87,115,122,132-139 | 25 (12 open, 8 not yet read, 5 change proposed) | party first met here |
| Cephala's voice: a prim little girl with a dry streak (part 2 of 3) (`voice-cephala-2`) | 3:140-150,170,175,180,188-189,196,199-200,206,214,219,228,236,241 | 25 (23 not yet read, 2 change proposed) | party first met here |
| Fontana's voice: a polite boy who has to lead (part 1 of 3) (`voice-fontana-1`) | 3:0-2,7-8,12,18-21,67-68,70,72-75,77,82,84,88,93-94,96,98 | 25 (11 open, 9 change proposed, 5 not yet read) | lines placed here |
| Fontana's voice: a polite boy who has to lead (part 2 of 3) (`voice-fontana-2`) | 3:97,100,109-111,117,151,153-155,157,160-161,163,165-166,171,176,181,190-191,197,201,207-208 | 25 (16 not yet read, 5 open, 4 change proposed) | party first met here |
| Rosea's voice: gentle, genteel, easily flustered (part 1 of 2) (`voice-rosea-1`) | 2:98,104,110,125-129,131-141,158,164,170,176,181,187 | 25 (23 not yet read, 2 change proposed) | lines placed here |
| Zaril's voice: a gruff tough with a soft center (part 2 of 4) (`voice-zaril-2`) | 3:172,177,182-183,192,202,209-210,216,222,231,243,249; 5:57,60,63,67,70-71,74,77,83,86,92,95 | 25 (14 not yet read, 6 open, 5 change proposed) | party first met here |
| Zaril's voice: a gruff tough with a soft center (part 3 of 4) (`voice-zaril-3`) | 3:250,255,261; 5:1-2,26-28,31,33-43,45,48-49,89,113 | 25 (16 open, 5 change proposed, 4 not yet read) | party first met here |
| Zaril's voice: a gruff tough with a soft center (part 1 of 4) (`voice-zaril-1`) | 3:3,13,33-34,36-38,78,80,85,112,118,167; 5:0,5,20-21,23-25,54 | 21 (13 open, 7 change proposed, 1 not yet read) | party first met here |
| Fontana's voice: a polite boy who has to lead (part 3 of 3) (`voice-fontana-3`) | 3:215,220-221,229-230,237,242,247-248,254,260,278 | 12 (6 open, 4 not yet read, 2 change proposed) | party first met here |
| Reiran's voice: a cheeky Faerie Ninja who plays big sister (part 2 of 2) (`voice-reiran-2`) | 2:220,225,230,235,242,247; 3:9,11,270-272 | 11 (6 change proposed, 5 not yet read) | lines placed here |
| Rosea's voice: gentle, genteel, easily flustered (part 2 of 2) (`voice-rosea-2`) | 2:191,197-198,205,212,217,223,239-240,245 | 10 (7 not yet read, 3 change proposed) | lines placed here |
| Cephala's voice: a prim little girl with a dry streak (part 3 of 3) (`voice-cephala-3`) | 3:246,253,259,264 | 4 (4 not yet read) | party first met here |
| Read-through: Identify, Recovering your dead and 2 more (`read3-03`) | 3:152,162 | 2 (2 not yet read) | party first met here |

### Before chapter 3: The Underground Shrine and the blue stone

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) (`voice-bergamot-1`) | 4:9-13,32-33,38-39,51-52,58,62,71-77,87,90,93,97,102 | 25 (17 change proposed, 7 open, 1 not yet read) | lines placed here |
| Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) (`voice-cleo-1`) | 4:0-8,22-23,30,35-36,41-43,45-47,49-50,53-54,56 | 25 (22 open, 3 change proposed) | lines placed here |
| Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) (`voice-cleo-2`) | 4:57,60-61,64-70,78-83,86,89,92,95-96,100-101,105,108 | 25 (18 open, 6 change proposed, 1 not yet read) | lines placed here |
| Cresson's voice: the nervous assistant who knows too much (part 1 of 2) (`voice-cresson-1`) | 4:14-21,24-29,31,34,37,40,59,63,84-85,88,91,94 | 25 (15 open, 5 not yet read, 5 change proposed) | lines placed here |
| Cresson's voice: the nervous assistant who knows too much (part 2 of 2) (`voice-cresson-2`) | 4:99,104,107,110,113,116,119-120,125,128,131,138,140,143,146,149-150,152-155,161-162 | 23 (12 open, 7 change proposed, 4 not yet read) | lines placed here |
| Bergamot's voice: a grumpy old man, not a hillbilly (part 2 of 2) (`voice-bergamot-2`) | 4:98,103,106,109,112,115,118,124,127,130,134-137,139,142,148 | 17 (14 change proposed, 2 not yet read, 1 open) | party first met here |
| Cleo's voice: the pleasant professor, all the way to the end (part 3 of 3) (`voice-cleo-3`) | 4:111,114,117,121-123,126,129,132-133,141,144,147 | 13 (11 not yet read, 1 open, 1 change proposed) | party first met here |

### Before chapter 9: Area B: the black stone

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| Zaril's voice: a gruff tough with a soft center (part 4 of 4) (`voice-zaril-4`) | 5:51,53,119 | 3 (2 open, 1 not yet read) | lines placed here |
| Read-through: Menu labels and Zaril's party rescued (`read5-02`) | 5:121 | 1 (1 not yet read) | lines placed here |

### Before chapter 10: Area B: the red stone

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| The voice from the shadow: four speeches, and Agan (`npc5-10-shadow`) | 5:103-112 | 10 (5 not yet read, 3 change proposed, 2 open) | lines placed here |

### Before chapter 12: Area C: the silver stone

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| The pit trap (`npc3-11-pit-trap`) | 3:90-92,102,108 | 5 (5 open) | lines placed here |
| A man's voice: the pit rescuer, and Bergamot in the dark (`voice-voice-1`) | 3:95,99; 4:48 | 3 (2 open, 1 change proposed) | lines placed here |

### Before chapter 17: Area E: the control room

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| Read-through: The control room, Introductions and 5 more (`read4-01`) | 4:55 | 1 (1 not yet read) | lines placed here |

### No chapter known

| Review-tool scene | Lines | Count | Why this chapter |
|---|---|---|---|
| No open review scene (`none`) | EV:288 | 1 (1 check in play) | no chapter: confirm in play |

## Lines placed in each chapter

The lines a bot run or the walkthrough puts in a chapter, for knowing what the monitor will stop on there. Evidence is bot, walkthrough or map.

### Chapter 2: The Shrine and the jade mask

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Balbo's party | 2.13 Introductions | 2:98 | Rosea's voice: gentle, genteel, easily flustered (part 1 of 2) | bot 1 |
| Balbo's party | 2.20 Talk: told them | 2:217 | Rosea's voice: gentle, genteel, easily flustered (part 2 of 2) | bot 1 |
| Balbo's party | 2.20 Talk: told them | 2:220 | Reiran's voice: a cheeky Faerie Ninja who plays big sister (part 2 of 2) | bot 1 |
| Balbo's party | 2.22 Other parties: Guy | 2:176 | Rosea's voice: gentle, genteel, easily flustered (part 1 of 2) | bot 1 |
| Balbo's party | 2.23 Other parties: Fontana | 2:181 | Rosea's voice: gentle, genteel, easily flustered (part 1 of 2) | bot 1 |
| Balbo's party | 2.28 Talk: personal | 2:230 | Reiran's voice: a cheeky Faerie Ninja who plays big sister (part 2 of 2) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:12 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Fontana's party | 3.6 The first-meeting speech | 3:74 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |

### Chapter 3: The Underground Shrine and the blue stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:1 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:0-1,3,5-6,8 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | walkthrough 2, map 4 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:152-155 | Cresson's voice: the nervous assistant who knows too much (part 2 of 2) | map 4 |
| Cleo's group (the scholars) | 4.10 The glyph check | 4:161-162 | Cresson's voice: the nervous assistant who knows too much (part 2 of 2) | walkthrough 2 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:56 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | walkthrough 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:57 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | walkthrough 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:58 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | walkthrough 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:59 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | walkthrough 1 |
| Cleo's group (the scholars) | 4.8 Healing | 4:64-70 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | walkthrough 7 |
| Cleo's group (the scholars) | 4.8 Healing | 4:71-77 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | walkthrough 7 |

### Chapter 4: The lake machine

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:3 | Zaril's voice: a gruff tough with a soft center (part 1 of 4) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:13 | Zaril's voice: a gruff tough with a soft center (part 1 of 4) | bot 1 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:7 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.10 The glyph check | 4:84 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | bot 1 |
| Cleo's group (the scholars) | 4.11 Talk: news and told them | 4:92 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.11 Talk: news and told them | 4:93 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 1 |
| Cleo's group (the scholars) | 4.11 Talk: news and told them | 4:94 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | bot 1 |
| Cleo's group (the scholars) | 4.16 Talk: news | 4:129 | Cleo's voice: the pleasant professor, all the way to the end (part 3 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.16 Talk: news | 4:130 | Bergamot's voice: a grumpy old man, not a hillbilly (part 2 of 2) | bot 1 |
| Cleo's group (the scholars) | 4.16 Talk: news | 4:131 | Cresson's voice: the nervous assistant who knows too much (part 2 of 2) | bot 1 |

### Chapter 6: Area X and the white stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.4 The STAFF statue | 3:67-68,70 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1, walkthrough 2 |
| Cleo's group (the scholars) | 4.5 The tablet at the central computer | 4:30,35-36,41 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | bot 4 |
| Cleo's group (the scholars) | 4.5 The tablet at the central computer | 4:31,34,37,40 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | bot 4 |
| Cleo's group (the scholars) | 4.5 The tablet at the central computer | 4:32-33,38-39 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 4 |

### Chapter 7: Area A: the green stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:4 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:95-96,100-101,105 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | bot 5 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:97,102 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 2 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:98,103,106 | Bergamot's voice: a grumpy old man, not a hillbilly (part 2 of 2) | bot 3 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:99,104,107 | Cresson's voice: the nervous assistant who knows too much (part 2 of 2) | bot 3 |
| Cleo's group (the scholars) | 4.2 Greetings that react to your party | 4:11 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 1 |

### Chapter 8: Area A: the yellow stone and the Jail Ogre

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Balbo's party | 2.24 Other parties: Zaril's split | 2:187 | Rosea's voice: gentle, genteel, easily flustered (part 1 of 2) | walkthrough 1 |
| Fontana's party | 3.7 Zaril walks out | 3:75,77,82,84,88 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1, walkthrough 4 |
| Fontana's party | 3.7 Zaril walks out | 3:78,80,85 | Zaril's voice: a gruff tough with a soft center (part 1 of 4) | walkthrough 3 |
| Fontana's party | 3.7 Zaril walks out | 3:79,87 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | walkthrough 2 |

### Chapter 9: Area B: the black stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:2 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Fontana's party | 3.1 Greetings | 3:6 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 1 |
| Fontana's party | 3.1 Greetings | 3:9,11 | Reiran's voice: a cheeky Faerie Ninja who plays big sister (part 2 of 2) | walkthrough 2 |
| Fontana's party | 3.18 Other parties: Zaril | 3:197 | Fontana's voice: a polite boy who has to lead (part 2 of 3) | walkthrough 1 |
| Fontana's party | 3.18 Other parties: Zaril | 3:199-200 | Cephala's voice: a prim little girl with a dry streak (part 2 of 3) | walkthrough 2 |
| Fontana's party | 3.2 Farewells | 3:16 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:108 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | walkthrough 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:109 | Bergamot's voice: a grumpy old man, not a hillbilly (part 2 of 2) | walkthrough 1 |
| Cleo's group (the scholars) | 4.12 Other parties: Guy, Balbo, Fontana, Zaril | 4:110 | Cresson's voice: the nervous assistant who knows too much (part 2 of 2) | walkthrough 1 |
| Cleo's group (the scholars) | 4.2 Greetings that react to your party | 4:20 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | bot 1 |
| Zaril's party | 5.14 Zaril's party rescued | 5:119 | Zaril's voice: a gruff tough with a soft center (part 4 of 4) | bot 1 |
| Zaril's party | 5.14 Zaril's party rescued | 5:121 | Read-through: Menu labels and Zaril's party rescued | walkthrough 1 |
| Zaril's party | 5.4 Introductions | 5:26-28,31,33-34 | Zaril's voice: a gruff tough with a soft center (part 3 of 4) | walkthrough 6 |

### Chapter 10: Area B: the red stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:8 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:21 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Zaril's party | 5.1 Unnamed greetings and farewells | 5:1 | Zaril's voice: a gruff tough with a soft center (part 3 of 4) | bot 1 |
| Zaril's party | 5.1 Unnamed greetings and farewells | 5:5 | Zaril's voice: a gruff tough with a soft center (part 1 of 4) | bot 1 |
| The shadow | 5.10 The shadow's warning | 5:103-105 | The voice from the shadow: four speeches, and Agan | bot 3 |

### Chapter 12: Area C: the silver stone

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.8 The pit in the rubbish room | 3:90-92,102,108 | The pit trap | walkthrough 5 |
| Fontana's party | 3.8 The pit in the rubbish room | 3:93-94,96,98 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | walkthrough 4 |
| Fontana's party | 3.8 The pit in the rubbish room | 3:95,99 | A man's voice: the pit rescuer, and Bergamot in the dark | walkthrough 2 |
| Fontana's party | 3.8 The pit in the rubbish room | 3:97,100 | Fontana's voice: a polite boy who has to lead (part 2 of 3) | walkthrough 2 |

### Chapter 14: Area D: mimicry mode released

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.1 Greetings | 3:7 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 1 |
| Fontana's party | 3.2 Farewells | 3:18-20 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | bot 3 |
| Fontana's party | 3.26 Fontana's god-word hint | 3:278 | Fontana's voice: a polite boy who has to lead (part 3 of 3) | walkthrough 1 |
| Fontana's party | 3.5 The maze changes | 3:72-73 | Fontana's voice: a polite boy who has to lead (part 1 of 3) | walkthrough 2 |
| Cleo's group (the scholars) | 4.1 Greetings and farewells | 4:2 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | bot 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:60-61 | Cleo's voice: the pleasant professor, all the way to the end (part 2 of 3) | bot 2 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:62 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 1 |
| Cleo's group (the scholars) | 4.7 Introductions | 4:63 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | bot 1 |
| The shadow | 5.10 The shadow's warning | 5:106 | The voice from the shadow: four speeches, and Agan | bot 1 |

### Chapter 15: Area C: the demon statue

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Cleo's group (the scholars) | 4.3 Cleo after the maze changes | 4:22-23,42-43 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | walkthrough 4 |

### Chapter 17: Area E: the control room

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.2 Farewells | 3:30 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 1 |
| Fontana's party | 3.3 Greetings that react to your party | 3:52-53 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 2 |
| Cleo's group (the scholars) | 4.6 The control room | 4:45-47,49-50,53-54 | Cleo's voice: the pleasant professor, all the way to the end (part 1 of 3) | bot 7 |
| Cleo's group (the scholars) | 4.6 The control room | 4:48 | A man's voice: the pit rescuer, and Bergamot in the dark | bot 1 |
| Cleo's group (the scholars) | 4.6 The control room | 4:51-52 | Bergamot's voice: a grumpy old man, not a hillbilly (part 1 of 2) | bot 2 |
| Cleo's group (the scholars) | 4.6 The control room | 4:55 | Read-through: The control room, Introductions and 5 more | bot 1 |
| The mysterious man | 5.11 The mysterious man's warning | 5:107 | The voice from the shadow: four speeches, and Agan | bot 1 |

### Chapter 19: The ring for the Priestess's Door (bot-only detour)

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Fontana's party | 3.2 Farewells | 3:29 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 1 |
| Fontana's party | 3.3 Greetings that react to your party | 3:51 | Cephala's voice: a prim little girl with a dry streak (part 1 of 3) | bot 1 |
| Agan | 5.13 Agan | 5:112 | The voice from the shadow: four speeches, and Agan | bot 1 |

### Chapter 18: Area Z and the ending (walkthrough 18-19)

| Party | Topic (npc-map) | Lines | Review-tool scene | Evidence |
|---|---|---|---|---|
| Cleo's group (the scholars) | 4.4 Cresson's epilogue | 4:24-29 | Cresson's voice: the nervous assistant who knows too much (part 1 of 2) | walkthrough 6 |
| The mysterious man | 5.12 The mysterious man in Area Z | 5:108-111 | The voice from the shadow: four speeches, and Agan | bot 4 |

## Lines with no chapter (237)

Talk-menu, healing, identify, shop and greeting lines that play whenever a party is met and a topic picked. They count toward the chapter where the party is first met:

- Balbo's party: 34 lines, from chapter 2
- Fontana's party: 106 lines, from chapter 2
- Cleo's group (the scholars): 60 lines, from chapter 3
- Zaril's party: 36 lines, from chapter 9
- Event script: 1 lines, from chapter None
