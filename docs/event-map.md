# Event script scene map (EVENTMES.BIN)

This maps the 317 event strings to the scenes they belong to, in play order as far as
the sources allow, and lists every clue, item and word that links one scene to another.
Use it while reviewing: before signing off a string, look up its scene here, then check
the "Setups and payoffs" entries it appears in, so the English keeps every link the
Japanese makes.

## Sources and conventions

- **EV n** is EVENTMES string n (section 0). **NPCk n** is NPC_MESk.OBJ string n.
  **SISETU n** is the tavern and castle file, where the Fortune Teller (330-359) and the
  King (322-329) speak. **Catalog** is the monster compendium, M_CATALG.DAT.
- **FAQ** and **Tips** are the Dimguil FAQ and tips pages of the Japanese fan site
  Emonoya (emonoya.net), read in the Bartok's Trading Post mirror. **Enc.** is the same
  site's encounter tables, whose "fixed encounter" and "event party" pages give the
  floor and square of each scripted fight. That is how most scenes below are placed.
- Coordinates are written as the FAQ writes them: "B4F E5 N13" is five squares east,
  thirteen north. A prime (A', D') means that area after mimicry mode is released.
- The Japanese is authoritative. Each claim says where it comes from: **Game** (the
  text itself), **FAQ**, **Tips**, **Enc.**, or **Inferred** (my reading, which could
  be wrong). String order in the file is loosely grouped by area, and is used as weak
  evidence where nothing better exists; it is marked when used.
- The mirror's English says "Temple" for 神殿 and "Training Dungeon" for 練武場. This
  project uses Shrine and Training Maze.

## The story and the progression

**The premise (Game: SISETU 329, 331, 332).** On a festival night the Priestess (巫女)
went to the Shrine with three guards for the yearly rite and vanished. The Royal Guard
found bodies at the altar and no Priestess. The King of Ganess sends the party to
rescue her and find out what is happening underground. The lake beside the town
supplies the kingdom's "magic water", which it sells (NPC4 151); the lake has been
fouled and the town shaken by quakes (SISETU 327, EV 66, EV 68).

**The route (FAQ, Enc., Tips; the order within an area is partly inferred).**

1. **The island (Field).** Four stone pillars stand at the island's corners, carved
   with a tiger, a dog, a bird and a snake. Each hides a beast; each beast drops a
   stone piece. The four pieces join into the LITHOGRAPH OF SUN (太陽の石板) and open
   the sun-crested door in front of the Shrine. (Game: EV 11-13, 24-31, 48-51,
   289-292; Enc. places the four fights at the island corners.) Alstron explains that
   a seal is made by placing magical items at regular points around the thing sealed
   (NPC1 105-111).
2. **The Shrine interior, 1F-4F.** Murals and signs teaching the ancient script, the
   bird skeleton and the birdlime switch, the JADE MASK (4F), Murphy's Ghost (1F), and
   the altar room with the DIMGUIL mural and the Fire Golem (2F), which is optional
   and far too strong for now.
3. **The Underground Shrine, B1-B4,** through the moon-crested door (the LITHOGRAPH
   again). The scholars' archive, the man frozen in ice, the machine that fouls the
   lake (stopping it ends the quakes and restores the lake: SISETU 327), the first
   Guardian party, the blue stone (the first stone set into the LITHOGRAPH), the
   waterway, the "sky fell" inscription on B4F, and the 2-Head Snake guarding a
   winding machine that opens the elevator to Area X.
4. **Area X,** a hub with four sealed doors (A-D) and a central computer: a pedestal
   of 26 small tablets, one per ancient letter, where the LITHOGRAPH goes and a word is
   typed. The white stone and the word STAFF are in the north-east; typing STAFF opens
   Area A. Each later area is opened the same way with a word found in the area before.
5. **Area A** (password STAFF): the four golden corpses and the gold equipment, the
   green stone, the red and green crest doors, the Jail Ogre's cage (where Guy's party
   is rescued) and the yellow stone, and the word LABORATORY.
6. **Area B** (LABORATORY): the black stone, Zaril's party fused into a Chimera
   Warrior, the three-ring dial that opens the heretics' treasure vault, the Ruby Hand
   and the red stone, and the word WAREHOUSE.
7. **Area C** (WAREHOUSE, plus the black stone): the rubbish room, the moving-floor
   switches, the Greater Golem, the silver stone, the snake door and the damage floor
   (crossed with the JADE MASK), and the word ENERGY.
8. **Area D** (ENERGY): the spell-sealing room, the altar that demands the god's name
   (DIMGUIL), the word COCKPIT, and the small door that only a character in all four
   pieces of gold equipment may pass. Inside, a crystal is crushed and a voice
   announces "mimicry mode" released: the stone labyrinth turns to metal (EV 224, 237).
   The King rewards the party and says the depths are "not of this world" (SISETU 326).
9. **After mimicry mode.** New rooms open in the old areas (A' to D'). In A' a dome
   poses a riddle whose answer is GAME; the Crystal Man falls and leaves the gold
   stone, the eighth and last (FAQ; Tips give the order blue, white, green, yellow,
   black, red, silver, gold). A door appears in the middle of Area X; COCKPIT opens it.
10. **Area E** (COCKPIT): a hidden door on B4F leads to the control room, where the
    scholars Cleo and Bergamot reveal that they and their fellow heretics (邪教徒) took
    the Priestess, set monsters on the altar and laid out the ancient letters, all to
    find the "Opener of the Door" (扉を開く者). They fight the party (NPC4 44-55; Enc.
    places this at E B4F E12 N12).
11. **Area Z and the ending.** A mysterious man explains that the "Shrine" is a great
    iron ship that crashed long ago, that its leaking fuel changed this world's life,
    and that his failed experiments ended with crossing "our father" with a suitable
    creature; he invites the party to face "my father, who is also myself" (NPC5
    107-111). In a huge coffin lies a god; when it falls the Priestess appears, speaks
    an oracle, and gives the RING OF MEDIUM (巫女の腕輪) as proof to take home (EV
    229-236, 298). The King's closing speech says the Priestess was fated not to
    return (SISETU 322). Enc. puts Quetzalcoatl at Area Z E10 N10, and the Catalog
    describes him as the heretics' one god, "water, sun and creator"; that he is the
    thing in the coffin is **Inferred**.
12. **The golem route (FAQ, Tips).** A strong party can skip ahead: the Fire Golem
    (Shrine 2F), then the Shadow Golem (Underground B3), then the final boss. The two
    Priestess speeches (EV 234 and 236) probably belong to the two routes: 236 begins
    "You who believe in power alone: I have no tale to tell you". **Inferred.**
13. **After the ending.** The Training Maze (one floor deeper per stone set, eight in
    all; the Priestess's Door on B8F opens only for a body matching the Priestess's,
    which the RING OF MEDIUM provides) and the Dragon's Cave (opened with the DEMON'S
    STATUE from Area C'; the Diamond Knight party guards the MAGIC AMULET). Agan hints
    at the Dragon's Cave (NPC5 112).

**The hidden story (Inferred, from the pieces listed under "The ship" and "The
experiments" in the Setups section).** The Shrine is a crashed starship. The ancient
script is English, and the glyph words name ship rooms (COCKPIT, CONTROL, BRIDGE,
SHUTTLE, TRANSPORTER, COLDSLEEP, FREEZER, LABORATORY, ENERGY, CORE, COMPUTER). The
lake's "magic water" is the ship's leaking fuel. Mimicry mode is the disguise that made
the ship look like a stone temple. The survivor's experiments are the tanks, the eggs
and the experiment log. The heretics are the keepers of the ship's god, waiting for
someone to open its door. The Priestess was taken for the survivor's last experiment
and her soul absorbed (EV 282, NPC4 50, NPC5 111), which is why she can appear only
as a vision and not come home.

**The Fortune Teller** (SISETU 330-359) offers topics that roughly follow the
progression. They are listed under Setups and payoffs; several are the only hint for a
puzzle.

## Scenes

Scenes are numbered in play order as best established. Where the location is unknown
the scene sits with its likely area and says so.

### Town and the message boards

**S1. The message boards.** EV 1-9.
Where: not established (boards in the maze or town; nothing places them).
What: nine notes, mostly to someone called Jade. They are flavor with three puzzle
hints hidden among them.
- 1 Attention: have you forgotten any equipment, is everyone's status normal. Starts
  the "forgetting" motif (see Setups).
- 2 Fortunes told, in the tavern: points to the Fortune Teller, who gives several
  puzzle hints.
- 3 To Jade: meet at the Shrine at three tonight. Flavor.
- 4 No graffiti, no camping on pits, no casting Malor into rock. Series jokes; the
  graffiti ban is undercut by board 9.
- 5 To Jade: a thief took everything from the vault (金庫) but left "that red thing",
  locked it again, and leaves a hint for opening it: north is 0, south is 180. This is
  the angle convention for the three-ring dial (S33) and "the red thing" is the red
  stone in the vault (S34). Puzzle.
- 6 Dangerous floors: three combinations, three doors, the switches show directions,
  find the law of the moving floors; and don't forget the mask. Area C's moving-floor
  panel (S38) and the damage floor that needs the JADE MASK (S41). Puzzle.
- 7 To Jade: free tonight, how about GAME at the tavern (GAME in ancient letters,
  uncolored). Teaches G, A, M, E and plants the riddle answer for the dome (S49).
- 8 Training Maze advertisement: monster capture rate up. The Training Maze's card
  chests (S55); "capture" means monster cards. **Inferred.**
- 9 To Jade: turned down by the tavern waitress, leaving town, farewell; signed with a
  PS in ancient letters, TREBOR SUX. FAQ: Werdna's graffiti from Wizardry I, unrelated
  to the scenario.

### The island

**S2. The four pillars.** EV 24-31, 48-51, 289-292.
Where: the island's corners. Enc.: tiger at E2 N20, dog at E20 N2, bird at E2 N2,
snake at E20 N20 (the fights are named for Aztec day signs: Oserotoru, Inkuintori,
Cuautori, Coatl). The Catalog calls them guardians of the Cara Acol temple and the
"Four Pillar Gods".
What: touch a pillar (24, 26, 28, 30), it sinks into the ground and its beast attacks
(48-51; the snake is "cold-eyed", the others "savage-eyed"). The win gives STONE OF
TIGER, BIRD, DOG, SNAKE (289-292).
Branches: 25/27/29/31 "you examine it, but nothing happens" (probably after the stone
is taken; not established).
Oddity: 289-292 say the monster "came out of the statue" (彫像), though the scene is a
pillar (石柱) throughout.
Links: NPC1 105-111 (Alstron on seals placed around the Shrine); S3.

**S3. The sun door.** EV 10-16.
Where: in front of the Shrine (Game: 11). This is the entrance door Guy's party is
stuck at (NPC1 105).
What: a sealed door with the sun crest, the glyph word SUN, and a square hole.
Branches: 15 no stones ("Do we need something?"); 12 some pillar stones but not all
four; 13 all four join into the LITHOGRAPH OF SUN and the door opens; 14 later visits,
LITHOGRAPH already made; 16 "Haven't we forgotten something?"; 10 generic "shut tight,
no keyhole".
Links: SUN is the first glyph word most players decode, with the crest as its picture.
The square hole is the first of many (see "Square holes").

### The Shrine interior, 1F-4F

**S4. The bird skeleton and the birdlime switch.** EV 17, 42-45; alternative EV 301,
302 with NPC2 72-80.
Where: the Shrine floors (Game: window; Balbo's party is first met at Shrine 3F
E11 N6 per Enc.). Exact squares not established.
What: 17 a bird's skeleton lies in a window recess, and on a closer look a sticky white
substance gets on the party's hands. It is とりもち, birdlime, the paste used to trap
birds; the bird was caught in it. A side door needs two switches held at once. 43 a
switch springs back. 44 checking it again, the birdlime on your hand sticks to it and
it stays down. 45 with that switch held by the birdlime, you press the other one, the
door unlocks, and "the switch stays down". 42 is a plain switch that unlocks a lock.
Alternative (Inferred, strong): Balbo's party asks for help with exactly this kind of
door: two switches pressed at once or the side door won't open (NPC2 72-78). If you
agree, they count down and you press together (NPC2 79-80, duplicated as EV 301-302).
EV 45 and EV 302 end with the same sentence, the switch not springing back, which
suggests the same door. If you refuse Balbo, the birdlime is how you do it alone.
Scene purpose: puzzle, with a setup (17) that reads like flavor.
Links: Catalog bird entry (7:2): birds came into the Shrine through its windows, and
adventurers hunted them for their meat. Someone was trapping birds. **Inferred.**

**S5. The star ceiling.** EV 18-21.
Where: Shrine (file position). What: a door plaque reads STAR; a ceiling painted like
the night sky holds a shining jewel. 19 prompt; 20 touch it and the floor starts to
move; 21 declined. Teaches S, T, A, R; a moving-floor puzzle in miniature. Links: SUN
and MOON crest doors; the sun, moon and star pictures on Area C's switches (S38).

**S6. Murphy's Ghost.** EV 32, 52.
Where: Shrine 1F E6 N6 (Enc., Tips). What: a strange statue on a pedestal that
vibrates when touched; Murphy's Ghost appears (Tips). 52 later: "A statue? Nothing
unusual here." Links: the Fortune Teller's "Old Friend" topic (SISETU 333, 347): an
old friend awaits you. Murphy's Ghost is the series' famous old enemy from Wizardry I.
**Inferred.** Joke/flavor and an experience farm.

**S7. The altar room: the DIMGUIL mural and the Fire Golem.** EV 0, 35-38.
Where: Shrine 2F; Fire Golem at E11 N12 (Enc.). The FAQ says the god's name is written
on the mural in the room where the Fire Golem appears, so EV 0 is here.
What: 0 a huge mural, something painted in the middle, and in the lower right unknown
ancient letters: DIMGUIL (color 4). 35 a square monolith on the altar; "Could this be
connected to the Priestess?"; DON'T TOUCH written in blood on the floor; touch it? 36
nothing happens, or so it seems; a burning gaze from behind; too late (Fire Golem). 37
declined. 38 later, touching the altar does nothing.
Branches: first visit / touched / declined / after.
Purpose: story bait (the Priestess and the altar), a deadly optional fight, and the
god's name for Area D.
Links: SISETU 332 (bodies at the altar), 341 ("to learn the god's name, go to the
altar once more"); NPC1 289 (Guy saw baffling glyphs on a higher floor, "that altar
room?"); NPC4 50 (Cleo: we hid monsters at the Shrine's altar); NPC4 125 (Cresson:
beware the altars); NPC1 86-88/295 (Guy's party wiped out after touching an altar
statue; see S21); golem route (S54). The "burning gaze" is the Japanese 熱い視線, a
pun on the fire monster.

**S8. The JADE MASK.** EV 39-41, 293.
Where: Shrine 4F; Chany Mask at E14 N7 (Enc.; FAQ says 4F).
What: 39 a bloodstained mask made of jade hangs on the wall; take it? 40 it starts to
move (fight). 41 declined. 293 the fiend falls, only the bloodstained mask remains;
Obtained JADE MASK.
Purpose: setup for the damage floor in Area C (S41), which it reveals when equipped
(FAQ). It curses the wearer.
Links: SISETU 334 and menu 348 "The Mask" (the fiend's power, you will need it one
day); board 6 "don't forget the mask"; Catalog 5:13 (a puppet warrior whose bright red
mask is the real monster).

**S9. Shrine odds and ends.** EV 33, 34, 46, 47, 53, 54, 72, 73, 75, 227.
Where: mostly Shrine by file position; not established.
- 33/34 a door adorned with beautiful ornaments, locked / present. Purpose unknown.
- 46 "A desk?" nothing else. Probably the revisit line after the experiment log on a
  desk (S30). **Inferred.**
- 47 you look out of the window: nothing. Pairs with 17's window.
- 52, 53, 54, 227 "A statue?", "Nothing unusual", "A coffin?", "A bed?": revisit lines
  after an event object is used up (statue S6/S18, coffin S52, bed S21). **Inferred.**
- 72 a blank grave marker; 73 "Here lies a hero of many battles" followed by an
  unexplained code {ff18}. Location unknown.
- 75 the Shrine's exit door opens at a touch.

### The Underground Shrine, B1-B4

**S10. The moon door.** EV 80, 81.
Where: the way into the Underground Shrine (Enc. treats entering it as a milestone).
What: a door with the moon crest, the glyph word MOON, and a square hole. 80 the
LITHOGRAPH fits and it opens; 81 without it ("Do you need something?").
Links: SUN door (S3), STAR (S5).

**S11. The library.** EV 76, 106.
Where: the underground archive where the scholars Cleo, Bergamot and Cresson live
(NPC4; NPC3 206 calls it an archive to rival the royal library). 76 a door reads
LIBRARY. 106 old books crammed on shelves, nothing useful. Flavor, and home of the
scholars who turn out to be the villains (S50).

**S12. The freezer and the man in the ice.** EV 79, 55, 64, 65.
Where: Underground B3; Ice Rock at E20 N20 (Enc.).
What: 79 a door reads FREEZER. 55 a pillar of ice. 64 a figure inside the ice, its face
jutting out; reaching for it, the room shakes (Ice Rock fight). 65 the ice melts and a
path opens.
Links: SISETU 335 and menu 349 "The Freezer" (the man sealed in ice; his magic ends
only with his life). NPC2 261 (Balbo saw a frozen man and suspects a trap, and asks
for a "bridge"; はし could also be a ladder). Catalog 12:24 (a creature that loves the
cold and wears ice). FREEZER is the only word with Z.

**S13. The lake machine.** EV 66-70, 77, 78; Guardians EV 280.
Where: Underground B2; Gas Cloud at E11 N22, Guardian party at E7 N22 (Enc.).
What: 77 a door with no keyhole, water dripping from beneath. 78 a round hole where
water was sent to the lake, reeking and caked with filth. 66 a strange machine running
in a corner: "Is this what makes the Shrine shake?"; pull the lever? 67 steam fills the
room (Gas Cloud). 68 the steam fiend falls, the machine stops, the sound of flowing
water outside stops; will the tainted lake regain its power? 69 machine stopped
(after); 70 machine still humming (declined). 280 the Guardians: "you shall not cut off
the waters".
Purpose: story. This is the "fouled lake" and "quakes" thread.
Links: SISETU 336 and menu 350 "Strange Machine" (a machine underground fouled the
lake); SISETU 327 (King: the quakes have stopped and the lake has regained its magic);
NPC4 151 (the kingdom sells magic water that wells up without end); EV 210/211 (a
liquid thicker than the lake's water restores magic).

**S14. The blue stone.** EV 256-258.
Where: Underground; FAQ: start by dropping down the chute on B2F E22 N19.
What: a hollow in a wall with a blue stone stuck in it. 257 the LITHOGRAPH fits and the
blue stone sets into it. 256 plain (after). 258 without the LITHOGRAPH.
Slip in 258 (corroborated, see Translation traps): the first line says the stuck stone
is green, though this is the blue set; its closing thought has a bare "7" where {ff30}2
belongs. The current English copies the slip.
Links: NPC2 82-83 (Balbo: you too fitted the blue stone into the LITHOGRAPH); S15.

**S15. The waterway.** EV 87, 88, 129.
Where: Underground (FAQ: crossing the waterway needs the blue stone).
What: a shallow square hole in the floor, the size of the LITHOGRAPH. 88 set it and the
underground stream stops and parts, opening a path. 129 set it, nothing happens,
"Aren't we forgetting something?" (the blue stone isn't in yet). 87 plain description.
**The 87/88/129 split is Inferred from the FAQ.**

**S16. "The sky fell."** EV 105.
Where: Underground B4F E7 N15 (FAQ).
What: a message on the wall, in color 4: the sky fell; the birds of the sky (天) fled
clockwise to the east, the people fled counterclockwise to the north-east, the snakes
that crawl the ground (地) fled clockwise to the south-east. Is there a secret here?
Purpose: the whole solution to the three-ring dial in Area B (S33), found three areas
earlier. The FAQ tells players to note it down.

**S17. The 2-Head Snake and the winding machine.** EV 71, 82-85, 86.
Where: Underground B1; 2-Head Snake at E15 N12 (Enc.).
What: 71 something like a log lies in the room; it moves, its end splits into two
mouths (fight). 82/83 behind it, a strange machine with an immovable lever and a hollow
in the floor before it; 82 with the LITHOGRAPH (try it?), 83 without ("Aren't we
forgetting something?"). 84 the drum winds in the chain; 85 pays it out.
Result (FAQ): the mural by the elevator disappears and an elevator to Area X appears.
86 a door reads CORE (location not established; file position near here).
Links: Catalog 7:16 (holy places are often ruled by snakes).

**S18. The Shadow Golem's statue.** EV 59-63.
Where: Underground B3; Shadow Golem at E19 N12 (Enc., Tips).
What: 59 a strange statue on an altar, DON'T TOUCH written in blood; touch it? 61
nothing happens, or so it seems; an eerie light covers the statue and its shadow
spreads over the wall; too late (Shadow Golem). 62 declined. 60, 63 after.
Purpose: the second fight of the golem route (FAQ). Mirrors S7 almost word for word.
Links: Catalog 4:7 (a shadow golem cast by a strange statue); NPC1 86-88 and 295
(Guy: keep your hands off the statue on the altar; see S21 for which altar).

### Area X

**S19. The central computer.** EV 134-145, 58; NPC4 30-41.
Where: the middle of Area X (FAQ). The four doors on its sides are A-D.
What: 134/135 a pedestal of small tablets with a large square hole; 134 with the
LITHOGRAPH the tablets light up ("Maybe one of these buttons?"), 135 without. The
tablets are a keyboard of the 26 ancient letters (NPC4 33); the FAQ's hint for reading
the script is that the tablets follow a keyboard layout read down the columns. Typing
the right word lights a letter: 136-140 A to E (color 4), "it seems to have sensed
something vital". 141-145 the doors read A to E (color 4). 58 a door reads COMPUTER
(location not established).
Passwords (FAQ): STAFF opens A, LABORATORY B, WAREHOUSE C (with the black stone),
ENERGY D, COCKPIT the center door to E once all eight stones are set.
Links: NPC4 30-41 (the scholars find the tablets, "a switch", and leave it to you);
NPC2 84-85 (Balbo: the center of something, four doors that won't open, the small
tablets hold a secret); NPC3 67-71 (S20). The word "altar" in 178/179 ("Go to the
altar") probably means one of these keyboard altars.

**S20. STAFF and the white stone.** EV 268-270.
Where: Area X north-east (FAQ).
What: a small statue's pedestal with a square hole and a white shining stone; nearby
the glyph word STAFF (color 4). 268 the white stone sets into the LITHOGRAPH; 269
without it ("Aren't we forgetting something?"); 270 after.
Links: NPC3 67-71 (Fontana's party at this statue: a hole for the LITHOGRAPH, the
glyphs are a key; Artemisia: the small tablets had the same letters). STAFF is the
first password (S19).

### Area A (B1-B4)

**S21. The golden corpses.** EV 113-117, 294-297, 114, 227; Guardians EV 281.
Where: Area A B1; the zombies at E8 N16 (armor), E8 N8 (gauntlets), E15 N15 (boots),
E8 N11 (helm) (Enc.). Guardian party at B1 E16 N11 (Enc.).
What: corpses on beds wearing a golden helm, armor, gauntlets, boots; reaching for the
gear, the corpse twitches (fight). 294-297 Obtained GOLD HELM, BOOTS, GAUNTLETS, ARMOR.
114 a corpse with no gear (after mimicry mode only High Zombies appear: Tips). 227 "A
bed?" (probably after). 281 the Guardians: your bodies shall serve to remake our own.
Purpose: setup for the small door (S47), which needs all four pieces worn.
Links: SISETU 337 and menu 351 "Golden Warrior" (friend or foe, one clad in gold shall
shake heaven and earth: the small door and mimicry mode); EV 130 ("don't forget full
gear"). Tips: the pieces can be farmed until mimicry mode.
Guy's altar warning (NPC1 86-88, 295): his party touched an altar, a monster killed
everyone but him, and he warns you off "the statue on the altar". The word statue
(彫像) matches S18, but his party is met on the Shrine floors early (Enc.), where the
altar is S7's. Which altar he means is not established.

**S22. The green stone.** EV 262-267.
Where: Area A B4F E5 N13 (FAQ). There are two sets of strings (262-264, 265-267), each
with plain / set / without-LITHOGRAPH; why there are two is not established.
Links: FAQ: after setting the green stone, find the secret door at B4F E14 N11 to reach
the green door. NPC2 262 (Balbo: isn't the green stone enough? something is missing).

**S23. The light altars and the crest doors.** EV 89-98, 118-126, 133, 195, 92, 93.
Where: Area A (FAQ names a green door and a red door in Area A; the rest is Inferred
from file position and content).
What: 89 a strange altar sending a shaft of light to the ceiling; 90 nothing fits; 91 an
altar with a square hole. 95-98 set the LITHOGRAPH: the green stone blinks / the red
stone blinks / both blink, touch which? / nothing happens. 122 a hole in the floor with
a shaft of light; 123-125 the light is white and warm / green / red like fire; 126
nothing happens; 133 a device on the ceiling seems to drink the light; 195 a device
with light shining from its top. 118-121 a door with a red (or green) crest: lit and
unlocked, or locked.
FAQ: the red door opens after the red stone is set (Area B), "by the same procedure as
the green door". Beyond the green door a switch opens a chute at E17 N11 (not while
Litofeit is active).
92/93 doors reading FEMALE and MALE sit in this stretch of the file (location not
established).

**S24. The Jail Ogre's cage and the yellow stone.** EV 99, 102, 196, 259-261, 100, 101.
Where: Area A B4; Jail Ogre at E17 N12, after the fight E19 N12 (Enc.).
What: 99 beyond iron bars, murky dark and a stench of beasts; you grip the bars and the
door opens like a waiting trap, no way out, "Now what do we do?" (Jail Ogre). 102 the
bars unlocked (after). 196 a beast was kept here; stench, scraps of food. 259-261 bones
of many who were eaten; a wall hollow with a yellow stone; 259 set, 260 without, 261
after.
Rescue (Enc. "Guy party rescue"; NPC1 80-85, 104): Guy, the only survivor and
poisoned, thanks you for killing "that big green brute" that nearly ate them and asks
for Ruby Slippers; later he pays 10000 Gp, having lost all their items.
100/101 a stone coffin / a strange iron box, nothing inside (stone and iron: see
"Stone turns to metal"); location not established, file position here.
Links: SISETU 338 and menu 352 "The Imprisoned" (a chained, vast, green-glowing fiend
lies in wait); Catalog 7:17 (an ogre chained in a prison); NPC2 86-87 (Balbo: the iron
bars ahead seem off). The yellow stone's link to the ogre's lair is **Inferred** from
the bones and 196.

**S25. LABORATORY.** EV 107, 219, 220.
Where: Area A B4F E17 N20 (FAQ); reach it by the ladder on B3F E12 N20 and a secret
door. 107 a mural of someone wrapped in tubes, "some sort of experiment?", with
LABORATORY in the right corner (color 4). The picture teaches the word, and the word is
Area B's password. 219/220 ladders down / up (generic, used anywhere).

### Area B (B1-B5)

**S26. Entering the lab; the black stone.** EV 156, 277-279.
Where: Area B (FAQ: the black stone is set in Area B). 156 a door reads LABORATORY
(color 4). 277-279 a device with a square pedestal and a black stone: set / without /
after. FAQ: WAREHOUSE also needs the black stone.

**S27. The warp switches.** EV 306, 307 (and probably 197, 248).
Where: Area B B3F south-west and north-west, then B2F (FAQ). Pressing a switch once
makes a magic circle that warps you up a floor; pressing it again turns it off. 306
"something switched on"; 307 "something switched off" (party thoughts). The route
leads to the stairs to the dial (S33). FAQ: Guy tells you about the three discs here.

**S28. Zaril's party and the Chimera Warrior.** EV 150-152, 194; NPC5 118-121.
Where: Area B B3; Chimera Warrior and Skeleton Warrior at E12 N11 (Enc.).
What: 150 you meet Zaril's party; they flee in terror into the dark; huge footsteps;
you see them twisted together into one; they come at you as a huge fiend. 194 the same
with an unnamed party (if you never met Zaril's). 151 the fiend's bones knit back
together; 152 bones creak, "It's him!" (やつだ, "that one", not necessarily a person).
Afterward Zaril's party reappears, alive (NPC5 118-121: Gaura groans, Zaril yells,
Fritillaria cries for help, "a party suddenly appeared"; Enc. "Zaril party rescue").
Links: Catalog 12:27 (a chimera warrior made by heretics with three adventurers trapped
in its middle; Zaril's party has three members); EV 281 (Guardians remaking bodies);
EV 242 ("Experiment 2: Modification"); NPC3 75-89 (Zaril leaves Fontana's party).

**S29. The frost tank.** EV 153, 127.
Where: probably Area B' (Mutants at six squares on B'-B2: Enc.). **Inferred.**
What: 153 an eerie device in a dark room with a frost-covered tank; you wipe the frost
and the eyes of a creature inside glow (fight). 127 a wall reads COLDSLEEP (location
not established).
Links: NPC5 109 (the survivor's creatures crumbled once out of the tanks); Catalog 12:28
(a failed experiment that seems to beg for help).

**S30. The experiment log.** EV 242, 46.
Where: not established (a desk; LABORATORY suggests Area B).
What: a book on a desk (color 6): Experiment 1, land mines, success; 2, modification,
success; 3, growth, failure?; the enemy is coming sooner, so traps are being set; curse
the Royal Guard. 46 "A desk?" is probably the revisit.
Links: "Growth" failing = the eggs that hatch and never grow (S48, NPC5 109); the Royal
Guard (SISETU 326, 332); the TRAP and DANGER signs (S32, S37).

**S31. Right foot, left foot.** EV 166-168.
Where: not established (file position between Areas B and C). Two great pillars with
recently carved words, "For the right foot" and "For the left foot", and a switch
between them (167). Purpose not established. EV 228 "A huge pillar towers here" uses
the same noun (巨大な柱).

**S32. Other Area B doors.** EV 154, 155, 157, 169, 165.
154 TRAP, 155/157 PEOPLE murals (132 is a third), 169 a locked door with no keyhole,
165 a strange stand. Locations not established; file position Area B.

**S33. The three-ring dial.** EV 158-164.
Where: Area B, reached from B1F by stairs (FAQ).
What: 158 a door with a disc in three layers (円盤), locked; turn it? 160-162 how far
to turn the small, middle and outer ring. 163 nothing, it turns back. 164 "Success!"
159 later, unlocked.
Solution (FAQ): the small ring 135 degrees clockwise, the middle ring 45 degrees
counterclockwise (315 is wrong), the outer ring 90 degrees clockwise. Each ring must
stop exactly on its angle.
The chain of clues: EV 105 (who fled which way); SISETU 339 and menu 353 "Ring Door"
(have you found the three rings? the key is hidden on some wall; the large ring stands
for the sky, the small ring for the earth); board 5 (north is 0, south is 180, so the
answer is in degrees); NPC1 288 (Guy: three animals, a clue he saw somewhere); NPC2
88-89 (Balbo: turn the three discs, there must be a clue). Birds (sky) = outer ring,
snakes (ground) = small ring, people = middle.

**S34. The vault, the Ruby Hand and the red stone.** EV 149, 274-276; Guardians EV 282.
Where: Area B B5; Ruby Hand at E5 N12, Guardian party at E9 N12 (Enc.).
What: 149 you reach for a red stone set in the wall; cracks run across it; you have
woken something sleeping behind it (Ruby Hand). 275 in the small room, a hollow with
the red stone; it sets into the LITHOGRAPH. 276 without; 274 after. 282 the Guardians:
your souls go to our god, absorbed like the Priestess's.
Links: board 5 (the vault robbed, "that red thing" left behind): the vault is the room
behind the dial, and the red thing is this stone. Catalog 13:3 (a guardian of the
heretics' treasure vault, 宝物庫, a mineral body like a gem with a face and arms). FAQ:
after the Ruby Hand, saving before leaving can trap the party behind the restored wall
(first print only). **The dial-to-vault connection is Inferred** from board 5 and the
Catalog.

**S35. WAREHOUSE.** EV 178, 179.
Where: Area B B1F, on the head of a statue (FAQ). The event text calls it a pillar
(石柱); two identical strings.
What: recently carved words and ancient letters on the pillar's head: WAREHOUSE (color
4) and "Go to the altar". WAREHOUSE is the only word with W, so the glyph can't be
learned anywhere else.

### Area C (B1-B4)

**S36. TRASH and the rubbish room.** EV 173-177; NPC3 90-108.
Where: Area C; the Dust fights at four squares on C-B2 (Enc.). **Inferred** that the
room is here.
What: 173 the floor reads TRASH. 174 a big room like the inside of a rubbish bin; search
it? 175 only stones and dead animals, then something soft, and a huge heap of rubbish
attacks. 176 the same with scrap iron instead of stones (Area C', after the walls turn
to metal). 177 a stench; you step on a dead animal.
Links: NPC3 90-108 (a trap in a rubbish-strewn room sucks the party through the floor
like an antlion's pit; Fontana's party is down there too; Guy lowers a rope and tells
you to take a bath). JUNK (217).

**S37. Area C glyph words.** EV 170, 171, 172, 185.
170 a wall reads DANGER (probably near the damage floor: board 6's heading is
"Dangerous floors!", 危険, the same word). 171 a strange statue reads SHUTTLE. 172 a
huge box reads CONTAINER. 185 a huge ornament has been smashed. Locations not
established; file position Area C.

**S38. The moving-floor panel.** EV 183, 146-148.
Where: Area C B1 (FAQ calls it the B1F panel).
What: 183 a row of small switches in a corner; press them? 146-148 doors marked A, B, C
(color 5, unlike Area X's color-4 letters).
Solution (FAQ): nine switches; 1-3 set door A, 4-6 door B, 7-9 door C; each group sets
the first, second and third turning tile. The pictures: sun = east, moon = west,
mountain = south, star = north. Door C with the third group at south, east: the switch
that makes the stone appear. Door C with south, south, west, or door B with south,
east, south: the snake door. Door B with south, east, east: the Greater Golem.
Links: board 6 (three combinations, three doors, the switches show directions); SUN,
MOON, STAR glyph words (S3, S10, S5).

**S39. The Greater Golem.** EV 182, 288.
Where: Area C B2; Greater Golem at E11 N10 (Enc.).
What: 182 the huge fiend falls and a great hole opens in the floor. FAQ: the stairs
beside the hole lead nowhere until the switch at B4F E8 N12 is pressed (reached through
door C). 288 a switch: "Click." (probably that one).
Links: SISETU 340 and menu 354 "A Made God" (the idol the heretics made of their god was
unfinished); Catalog 4:8 (the mightiest golem, made in their god's likeness). The Fire
Golem is also made in the god's likeness (Catalog 4:6). Which golem the Fortune Teller
means is **Inferred** from the topic order (between the dial and the god's name).

**S40. The silver stone.** EV 271-273; Guardians EV 283.
Where: Area C (FAQ); Guardian party at C-B4 E5 N11 (Enc.). A device with a square
pedestal and a silver stone: set / without / plain. 283 the Guardians: this sword shall
drink your blood and our god shall rise.

**S41. The snake door, the damage floor, and ENERGY.** EV 184, 198.
Where: Area C (FAQ). 184 a door carved with a red snake and a blue snake. Beyond it a
damage floor; the JADE MASK, worn, shows the safe route (FAQ; or heal as you go, since
it leaves 1 HP). Past it, 198 a mural reads ENERGY (color 4), the password for Area D.
Links: S8, board 6, SISETU 334.

**S42. The SHUTTLE and the stone statue.** EV 186-188.
Where: Area C' B4F E21 N6, after mimicry mode (FAQ).
What: 186 the wreck of some vehicle, no way in, SHUTTLE on its side, a stone statue
lodged in one of its tubes; pull it out? 187 Obtained a strange stone statue (the item
is the DEMON'S STATUE). 188 declined.
Purpose: the key to the Dragon's Cave (S56).

**S43. The holy altar door.** EV 180, 181.
Where: not established (file position Area C). A door: "Holy altar beyond. Keep out."
The lock clicks open anyway (181: you touch it and it opens). Links: 178/179 "Go to the
altar"; NPC5 105 (the shadow: beyond lies the holy ground of the Opener of the Door).

### Area D (B1-B3)

**S44. The spell-sealing room and the magic pillars.** EV 210-212.
Where: Area D (FAQ: entering the room seals spells for about 1000 steps; a pillar there
restores MP). 210 a great stone pillar leaking a liquid thicker than the lake's water;
a touch restores magic. 211 the same pillar in iron (after mimicry mode). 212 one wall
made of something different: a secret.
Links: the lake and the magic water (S13); ENERGY.

**S45. The god's name.** EV 199-205; Guardians EV 284.
Where: Area D (FAQ); Mother at D-B3 E11 N19, Guardian party at D-B3 E10 N9 (Enc.).
What: 199 a wall like a giant needle; an altar with a square hole and many small
tablets; look closer? 200 declined. 202 nothing fits. 203 the LITHOGRAPH goes in, the
tablets light, a lifeless voice fills the room. 201 "Speak the name of the god!" (color
4). 204 "Wrong! Leave this place!" and "We seem to be forgetting something." 205
"Correct! Now receive your final baptism!"; the wall crumbles, a beautiful woman
appears but is an illusion, a woman's body clad in giant needles, "the guardian god of
this labyrinth?", attacks (probably Mother).
Answer: DIMGUIL (FAQ), shown in S7's mural.
Links: SISETU 341 and menu 355 "The God's Name" (go to the altar once more); NPC3 278
(Fontana: a word that stands for a god? not the god Kadorto; he'll ask the Fortune
Teller); NPC1 289 (Guy: glyphs in the altar room upstairs); NPC4 14 (Cresson, to a
character named after the god: that god is evil to us, change your name). 284 the
Guardians: hundreds of years to raise this land again.

**S46. COCKPIT.** EV 243.
Where: Area D B2F E2 N14 (FAQ). A mural reads COCKPIT (color 4): the password for the
center door of Area X, usable once all eight stones are set.

**S47. The small door and mimicry mode.** EV 130, 221-226, 218, 237.
Where: Area D (FAQ).
What: 130 words carved recently on a door: danger ahead, don't forget full gear. 221
the small door is shut tight. 222 your GOLD GAUNTLETS answer it and it opens; only one
can enter. 223 who will go in? 218 that character is in no state to. 224 the character
touches the crystal in the middle of the room; the tremor grows; they crush it; a voice
from the whole labyrinth, "Danger! Mimicry mode released." (color 6); everything
changes. 237 the stone walls turn to metal. 225 the character bursts out in flames and
turns to ash, "Did we forget something?"; 226 flames fill your sight, same thought
(the failure branches, without all four gold pieces: FAQ).
Links: S21 (the gold gear); SISETU 337 "Golden Warrior"; NPC2 264-265 (Balbo: Alba went
in and came out as ash); board 1 (forgotten equipment); after effects in S48 onward,
SISETU 326 (the King's reward), NPC1 98-103, NPC2 90-91, NPC3 72-73 (the NPCs notice
the maze has changed; Lychee protests she only kicked a pebble), NPC4 22-23, 42-43
(Cleo: not a maze built by a wizard; a trove of research material).
222 names only the gauntlets, though all four pieces are needed (FAQ).

### After mimicry mode

**S48. The egg.** EV 206-209.
Where: Area D'; Demon Babies at six squares on D'-B3 (Enc.). **Inferred.**
What: 206 in a warm room an egg clings to the floor, rock-hard but breathing; examine
it? 207 something waiting inside moves (fight). 208 the egg is gone. 209 yellow fluid
spurts out, too foul to touch.
Links: Catalog 10:24 (a demon infant fresh from its egg, a heretic lab creature); NPC5
109 (the survivor's creatures hatched from eggs and never grew); EV 242 ("Growth...
Failure!?").

**S49. The GAME dome and the gold stone.** EV 94, 103, 104, 108-112.
Where: Area A' B2; Crystal Man at E6 N5 (Enc.; FAQ: the unexplored part of Area A after
mimicry mode).
What: 103 an eerily glowing altar, small tablets, a clear round dome with a glow inside;
touching a tablet does nothing, "Aren't we forgetting something?" 108 with the
LITHOGRAPH the tablets light; touch one? 94 a voice from the device (color 4): I am not
reality but a mass of imagination; I need luck and wit and hold many hardships;
overcome them for a fruitless reward; what do you call my world? 109 you type whatever
comes to mind (wrong). 110 "Correct! Now, let us begin!" (Crystal Man). 111 the shining
demon falls and a stone glowing gold sets into the LITHOGRAPH. 112 declined. 104 "But
nothing happens."
Answer: GAME (FAQ).
Links: board 7 (GAME at the tavern); SISETU 342 and menu 356 "Strange Device" (a strange
machine, something like a GAME, don't think too hard; GAME in plain Latin letters);
NPC1 287 (Guy: since the maze changed, a strange device asks questions; he'll ask the
Fortune Teller); Catalog 12:30 (a guardian made with the maze's knowledge and machines).

**S50. The dreamlands.** EV 190-193.
Where: Area D' B1; Succubus around E0 N4, Incubus around E23 N4 (Enc.).
What: 190 recently carved on a door: MEN'S DREAMLAND; 191 rest on the bed, a beautiful
woman in a dream, a fiend when you wake. 192 WOMEN'S DREAMLAND; 193 a beautiful man.
Joke. Links: FEMALE and MALE doors (92, 93); the "beautiful woman" motif.

### Area E and the control room

**S51. Area E.** EV 131, 189, 213-217, 244, 245 (locations not established).
FAQ: the B3F switch restores HP and MP; a hidden door in the north wall of B4F E11 N21.
Guardian speech 285 probably belongs to the sixth Guardian party (location unknown).
Glyph words that sit late in the file or name the ship's command rooms: 244 CONTROL,
245 BRIDGE, 131 TRANSPORTER, 213 HEAL, 214 GAS, and the broken murals with faint
letters 189 REST, 215 MEATING (sic), 216 REVIVAL, 217 JUNK. **Placement Inferred.**
The control room fight with Cleo and Bergamot is NPC4 44-55 (no event strings). Cleo
greets the party "to the control room" (司令室), which is presumably behind the CONTROL
door.

### Area Z and the ending

**S52. The huge coffin.** EV 229-233, 235, 228.
Where: Area Z; Quetzalcoatl at E10 N10 (Enc.). **Inferred** that he is the one in the
coffin.
What: 229 a huge coffin in a huge room; touch the face-like relief on its front? 230 the
room shakes and the lid opens (fight). 231 too soon: "Have we left something undone?"
232 the relief is silent (after): "We shouldn't have forgotten anything..." 233 you
felled the one in the coffin (a god?), and the relief parts. 235 a wall with the relief
appears at once, then as 230 (probably arriving by teleport on the golem route). 228 a
huge pillar (location not established).
Links: NPC5 107-111 (the mysterious man: this is the real world; the iron ship; face my
father, who is also myself); SISETU 343 and menu 357 "Dark God" (a dark god asleep
below); Catalog 5:12; NPC2 263 (Balbo saw a statue of a giant face; not established
that it is this relief).

**S53. The Priestess and the RING OF MEDIUM.** EV 234, 236, 298, 299.
What: 234 a beautiful woman appears and speaks (color 2, set out in pairs): you who
know the nature of all things, is this place one or all; you who gained every power,
is this the end or the beginning; you who give off every light, is it past or future;
you must carry the answer; I, the Priestess who carries the god's word, must wait for
those who seek more; take the proof home and see everything as your heart bids. 236
the short version for one "who believes in power alone": no tale for you; take the
proof home. 298 the Priestess offers a bracelet; Obtained RING OF MEDIUM. 299
everything goes dark and you are sent somewhere (Tips: to the altar in the Shrine).
Ending: carrying the ring out of the maze starts the King's audience and the ending
(Tips); SISETU 322 (the Priestess was fated not to return; title and 1,000,000 Gp).
Links: NPC4 24-29 (Cresson: you became the Opener of the Door; tell the world what you
saw; I'll wait here for the next one), which mirrors the Priestess waiting "for those
who seek more"; SISETU 344 and menu 358 "The End".

**S54. The golem route and the X statue.** EV 304, 305 (with S7, S18).
FAQ: beat the Fire Golem and the Shadow Golem appears, then the final boss, then the
ending; after a title is awarded the final boss no longer appears. Tips: after the ring
you are teleported to the Shrine altar, and another party waiting there can take the
golem route again ("carry several LITHOGRAPHS OF SUN"). 304 a strange statue with an X
on its chest; 305 it answers the LITHOGRAPH, which shines, and you are whisked away.
**That 304/305 is the golem route's teleporter is Inferred.**

### After the ending

**S55. The Training Maze.** EV 246-248, 238-241.
Where: the eight-floor Training Maze from the Edge of Town; each stone set opens one
floor deeper (FAQ). 246/247 a strange little box, locked / unlocked with one card
inside; 248 a switch (Tips: the right switch unlocks a card chest). 240 the Priestess's
Door: ancient letters and numbers (color 4): STR 5, INT 18, PIE 18, VIT 5, AGI 5, LUC
18, LVL 5, AGE 18, SEX FEMALE, RACE ELF, CLASS PRIEST, and in modern letters,
Priestess's Door; the door is made to fit someone's body; will someone try? 238 no
match; 239 a match, a new room, a chill. 241 later, unlocked.
Solution (FAQ): an elf, female, 18-year-old level 5 Priest who uses the RING OF
MEDIUM's special power. The profile is presumably the Priestess's own (**Inferred**).
Links: board 8; NPC4 142 (Bergamot: the Training Maze has codes like the Shrine's).

**S56. The Dragon's Cave pedestal.** EV 249-255, 300.
Where: Dragon's Cave B3F, secret door at E9 N12 (FAQ); the Diamond Knight party at
E12 N12 (Enc.).
What: 249 a pedestal with a hollow; place something? 250 nothing fits. 251 the little
stone statue fits; the pedestal sinks. 252 a magic circle, "Is someone being sent
here?", a mysterious band appears (Diamond Knight party). 300 Obtained MAGIC AMULET. 253
the amulet reacts to the pedestal (already have it). 254/255 you leave.
Links: S42 (the statue); NPC5 112 (Agan: below lies a sealed place where monsters stir
that even the gods can't control).

### Anywhere

**S57. Otaka.** EV 311-315.
Where: random (FAQ: rarely found, e.g. Underground B3 or Area B; triggered by touching a
spinning magic circle). A programmer's hidden event (FAQ). 311 first meeting ("one of
the programmers"; "not a word to Agan!"), 312 later meetings, 313 no room, 314 items
given, 315 items given and already identified.
Links: Agan, NPC5 112 (see Setups). The game never gives Otaka's sex; the mirror's
English FAQ says "she", the voice sheet says "his".

**S58. Buried gold.** EV 308-310, 316.
Random search spots (Tips: most often by the green pot on Shrine 2F). 308 signs of
digging; search? 309 you search the rubble; 310 "Buried gold!" and the amount; 316
buried treasure.

**S59. Leftovers.** EV 286 "Clear", 287 "END", 303 "That's all for the game show"
(a trade-show demo). Not seen in normal play.

**S60. Unplaced one-liners.** EV 128 (a crystal floats by the ceiling; touch it?), 167
and 197 (switch prompts), 212, 104, 126.

**S61. The glyph-word signs** (for reviewing the carved-letters lines together). Words
not already placed above: 22 SHIP (a mural of people sailing to the Shrine), 23 DEATH
(a giant figure drawn like Death), 56 ENTER, 57 EXIT, 74 KING (a mural of a ruler), 132
PEOPLE. Locations not established; file position puts 22/23 early and 56-58, 74 with
the Underground strings.

## Setups and payoffs

Each entry lists every place the thing appears and what the link does. "Keep" notes
what the English must hold constant.

**The birdlime (とりもち).** EV 17 (paste on the hand, beside a bird skeleton in a
window), 43 (switch springs back), 44 (the paste holds it down), 45 (held by the paste,
the other switch opens the door). Catalog 7:2 (birds in the Shrine, hunted by
adventurers) explains why birdlime is there. Keep: 17 must read as a substance that
sticks, not a bird-droppings joke; "the sticky paste" in 44 and 45 must visibly be the
same stuff as 17's. The voice sheet already fixes this wording.

**The two-switch side door.** EV 42-45, EV 301-302, NPC2 72-80. The birdlime puzzle and
Balbo's countdown both hold two switches down to open a side door, and both end with
the switch staying down. Keep: EV 301/302 and NPC2 79/80 are the same Japanese; they
should read the same (the event file says "you", the NPC file says "we", and the NPC
file has "switch" where the event file has "switches"). Make 45 and 302 end in the same
words.

**The JADE MASK.** EV 39-41, 293 (Shrine 4F); SISETU 334, 348 (the fiend's power will be
needed); board 6 ("don't forget the mask"); EV 184 and the damage floor (Area C, FAQ);
Catalog 5:13 (the red mask is the real monster). Tips: equip it to see the route. Keep:
"mask" in board 6 and the Fortune Teller must be recognizably the jade mask; don't
vary it to "visor" or "face".

**GAME.** Board 7 (glyphs, uncolored), EV 94 (the riddle), 110 (correct), SISETU 342
(the Fortune Teller says GAME outright), NPC1 287 (Guy stuck on the device). The
answer is typed on the glyph keyboard. Keep: the riddle must still point at "game"
(imagined world, luck and wit, hardships, a prize with no substance). SISETU 342 says
"strange machine" (奇妙な機械) though its own topic title is "Strange Device" (奇妙な
装置) and the dome is a "device" in EV 94; "Strange Machine" is also the title of the
lake-machine topic. See the traps.

**The dial: "The sky fell," the rings, north is 0.** EV 105 (Underground B4F: birds of
the sky clockwise to the east, people counterclockwise to the north-east, snakes of the
ground clockwise to the south-east); SISETU 339, 353 (large ring = sky, small ring =
earth; the key is on some wall); board 5 (north 0, south 180); NPC1 288 (three
animals); NPC2 88-89 (three discs); EV 158-164 (small, middle, outer ring). Keep: sky
and earth (ground) in 105 so they map onto the Fortune Teller's large and small rings;
clockwise and counterclockwise; the exact compass points; the ring sizes named the
same way in 160-162 and SISETU 339 (small, and a word for the outer ring that matches
"large").

**The vault and "the red thing."** Board 5 (the vault robbed, the red thing left, the
lock hint); EV 158-164 (the dial door); EV 149 (a red stone in the wall, the Ruby Hand
behind it); EV 274-276 (the red stone set); Catalog 13:3 (the Ruby Hand guards the
heretics' treasure vault); FAQ (Ruby Hand, then the red stone). Keep: "red" in board
5; "vault" in board 5 should match whatever the Catalog calls the treasure room (the
Catalog English now says "treasury").

**TREBOR SUX and No Graffiti.** Board 9 (the signature, glyphs, color 5) and board 4
(No Graffiti, plus No camping on pits and No Malor into rock). The joke is the famous
graffiti under a graffiti ban, and board 4's other rules are series jokes (camping on a
pit, teleporting into rock). FAQ: Werdna's graffiti in Wizardry I, a password in IV,
seen again in VI and Gaiden III.

**Jade.** Boards 3, 5, 7 and 9 are all addressed to Jade (ジェイド): a date at the
Shrine, a burglar's note, a game invitation, a farewell. They read as one running
correspondence. In Japanese Jade has nothing to do with the JADE MASK (翡翠, a
different word); in English the two now share a word. See the traps.

**Glyph words: taught versus needed.** The script is English. Words that teach letters
come with a picture or context; words that are needed must be typed on a keyboard altar
or read to solve something. The needed words are the ones in color 4 (see the traps).

| Word | Where it appears | Role |
|---|---|---|
| SUN | 11 (sun crest door) | teaches S, U, N from the picture |
| MOON | 80, 81 (moon crest door) | teaches M, O |
| STAR | 18 (plaque, star ceiling) | teaches S, T, A, R |
| SHIP, DEATH, KING, PEOPLE | 22, 23, 74, 132/155/157 (murals) | taught by the pictures; SHIP foreshadows the iron ship |
| ENTER, EXIT | 56, 57 (doors) | teach X, among others |
| FEMALE, MALE | 92, 93 (doors) | teach F; needed to read SEX FEMALE on 240 |
| LIBRARY | 76 (the archive door) | teaches B, Y |
| FREEZER | 79 | the only Z |
| TRASH | 173 (rubbish room floor) | taught by the room |
| JUNK | 217 | the only J |
| STAFF | 268-270 (Area X, with the white stone) | **needed**: opens Area A |
| LABORATORY | 107 (Area A B4F mural of a tube experiment), 156 (door) | **needed**: opens Area B; the mural teaches it |
| WAREHOUSE | 178, 179 (Area B B1F) | **needed**: opens Area C; the only W |
| ENERGY | 198 (Area C, past the damage floor) | **needed**: opens Area D |
| COCKPIT | 243 (Area D B2F) | **needed**: opens Area E; K otherwise only in KING, JUNK |
| DIMGUIL | 0 (Shrine 2F mural) | **needed**: the god's name (201) |
| GAME | board 7 | **needed**: the riddle (94) |
| A-E | 136-145 (Area X), A-C 146-148 (Area C doors) | area letters |
| STR ... PRIEST | 240, 241 | the Priestess's Door profile |
| SHUTTLE, CONTAINER, DANGER, TRAP, CORE, COMPUTER, COLDSLEEP, TRANSPORTER, CONTROL, BRIDGE, HEAL, GAS, REST, MEATING, REVIVAL | various | ship-room labels; no puzzle role found |
| TREBOR SUX | board 9 | joke; teaches B, X |

No word contains Q, so the Q glyph can only come from the keyboard. Cresson's analysis
item and his "match rate" (NPC4 84-85, 161-162) track the player's decoding; Bergamot,
the heretics' expert in ancient writing (NPC4 127), claims he can't read the glyphs
(NPC4 11) though he helped lay them out (NPC4 50).

**The four pillar stones.** EV 24-31, 48-51 (the pillars and beasts), 289-292 (STONE OF
TIGER, BIRD, DOG, SNAKE), 12-13 (the pieces join into the LITHOGRAPH), NPC1 105-111
(the seal and the items around the Shrine), Catalog 5:8-11 (the Four Pillar Gods).
Keep: "pillar" consistently; 289-292 say "statue" in the Japanese (see the traps).

**The LITHOGRAPH OF SUN and its eight stones.** The tablet opens the sun door (13-14),
the moon door (80), runs the winding machine (82-85), parts the waterway (88), wakes the
keyboards (108, 134, 203), and teleports (305). Stones in play order (Tips):
- blue: 256-258, Underground (FAQ chute B2F E22 N19); NPC2 82-83
- white: 268-270, Area X north-east, with STAFF
- green: 262-267, Area A B4F E5 N13; NPC2 262; the green crest door 120-121, 95, 97, 124
- yellow: 259-261, Area A, the Jail Ogre's lair (Inferred)
- black: 277-279, Area B; also needed for WAREHOUSE (FAQ)
- red: 149, 274-276, Area B B5 vault; board 5; the red crest door 118-119, 96, 97, 125
- silver: 271-273, Area C
- gold: 111, Area A' dome (GAME)
Each stone set opens one more Training Maze floor (FAQ). The "Aren't we forgetting
something?" branch at each hollow means "you don't have the LITHOGRAPH with you".
Keep: the item name identical everywhere. The NPC files now say "Lithograph of the Sun"
(NPC2 82) and "the Sun tablet" (NPC3 68).

**Square holes and hollows.** Every place the LITHOGRAPH goes is a square hole (四角い
穴) or hollow (窪み): 11, 80, 82, 87-88, 91, 129, 134, 199, 257-275. The player learns
to read "square hole" as "the tablet goes here". Keep "square" wherever the Japanese has
it, and keep hole and hollow distinct as the Japanese does.

**The gold equipment.** EV 113-117 and 294-297 (Area A B1 corpses), 114 (after), 130
("don't forget full gear"), 221-226 (the small door; 222 mentions the gauntlets, the
FAQ says all four), SISETU 337, 351 ("Golden Warrior", one clad in gold shakes heaven
and earth), NPC2 264-265 (Alba burned to ash), Catalog 9:25-28 (the four zombies).
Keep: "gold" for the gear, and don't let the gold stone (111, "glows gold") read as the
same thing.

**The Priestess.** EV 35 (the monolith: connected to the Priestess?), 205 (a beautiful
woman who is an illusion), 234 and 236 (she speaks), 240-241 (her door), 282 (the
Guardians absorbed her soul), 298 (the ring). SISETU 322, 327, 329, 331, 332, 346. NPC1
0-6, 279; NPC2 72; NPC3 2, 74; NPC4 50 (Cleo took her), 121. Keep: 巫女 is always "the
Priestess"; her 腕輪 is the RING OF MEDIUM (298 bridges the two).

**The beautiful woman.** EV 191 (a dream, then a fiend), 205 (an illusion, then the
needle guardian), 234/236 (the Priestess). SISETU 331 calls the Priestess "fair". Keep
the same phrase so 205 reads as a false Priestess before the real vision.

**Zaril's party.** EV 150 (fused into one fiend), 194 (the unnamed version), 151-152;
NPC5 118-121 (they reappear); NPC3 75-89 (Zaril walks out on Fontana); NPC1 207-210,
NPC2 185-187, NPC4 108-110 (gossip about his new three-member party); Catalog 12:27
(three adventurers inside the chimera). Keep "Zaril's party" matching the NPC files.

**Otaka and Agan.** EV 311 ("not a word to Agan!"), NPC5 112 (Agan, the eternal
traveler carried into the past by demons, seeking the sealed place below: the Dragon's
Cave, S56). NPC5 72 (Fritillaria met a busy Fighter- or Lord-like man nobody else has
met, "maybe not from this world") may be Agan (**Inferred**). Nothing in the sources
explains Agan; he may be another staff cameo like Otaka (**Inferred**).

**Forgetting.** Board 1 (forgotten equipment), board 6 (don't forget the mask), EV 130
(don't forget full gear), EV 16, 83, 103, 129, 135, 258, 260, 264, 267, 269, 273, 276,
278 ("Aren't we forgetting something?"), 204 ("We seem to be forgetting something"),
225/226 ("Did we forget something?"), 231 ("Have we left something undone?"), 232 ("We
shouldn't have forgotten anything"), and 15/81 ("Do we need something?"). The party
thought is the game's standard "you're missing an item" signal. 130, board 1 and
225/226 form a small chain of their own: forgetting gear, and burning for it. Keep
"forget" in all of them.

**Stone turns to metal.** EV 237 (the walls turn to metal), 100/101 (stone coffin, iron
box), 175/176 (stones, scrap iron), 210/211 (stone pillar, iron pillar). The pairs are
the same object before and after mimicry mode. Keep stone versus iron or metal.

**The ship.** EV 22 (a mural of people sailing to the Shrine: SHIP), 186 (the SHUTTLE
wreck), the command-room words (COCKPIT, CONTROL, BRIDGE, TRANSPORTER, COLDSLEEP,
ENERGY, CORE, COMPUTER), 224 (mimicry mode), 237; SISETU 326 (not of this world); NPC4
22, 42 (not a wizard's maze); NPC5 108-110 (the great iron ship, the fatal accident, the
leaking fuel). Keep "ship" in 22 plain, so it can pay off.

**The experiments.** EV 153 (the frost tank), 206-209 (the egg), 242 (the log: land
mines, modification, growth failed), 150 (people fused); NPC5 109 (creatures that
crumbled out of the tanks, eggs that never grew); Catalog 10:24, 12:16, 12:27, 12:28.
Keep "growth" and "failure" plain in 242.

**Water, fuel and magic.** EV 66-70, 77, 78 (the machine and the filth), 68 (will the
tainted lake regain its power?), 210/211 (a liquid thicker than the lake water restores
magic), 280 (the Guardians forbid cutting off the waters); SISETU 327 (the lake regains
its magic), 336; NPC4 151 (magic water that wells up without end); NPC5 110 (fuel
leaking from the ship); Catalog 11:0 (ants grown huge in Lake Cara's water), 5:12 (the
god is water and sun). That the magic water is the ship's fuel is **Inferred**. Keep
"lake" and "water" plain and matching.

**Two quakes.** EV 66 (does this machine make the Shrine shake?), SISETU 327 (the quakes
have stopped); then EV 224 and SISETU 326 (a great tremor when mimicry mode is released).
Different causes; keep them apart.

**The Guardians.** EV 280-285, six speeches. Enc. lists six Guardian parties: Underground
B2 E7 N22, A B1 E16 N11, B B5 E9 N12, C B4 E5 N11, D B3 E10 N9, and one unknown. The file
order matches area order, and each speech fits its place (280 the waters, beside the
lake machine; 281 remaking bodies, beside the zombies; 282 the Priestess's soul, beside
the vault; 284 hundreds of years; 285 the last). **The pairing is Inferred.** The word
also names the Four Pillar Gods, the Gas Cloud, the Ruby Hand and the Crystal Man in the
Catalog; 205's "guardian god" is a different word (守り神).

**The heretics' planted hints.** EV 130, 166, 168, 178/179, 190, 192 are "recently
carved" words (modern script, unlike the glyphs). Bergamot says the heretics invited
people in, placed things to help them and set traps (NPC4 52); Cleo says they laid out
the glyphs (NPC4 50). **Inferred:** the recent carvings are theirs. Cresson warns about
altars (NPC4 125) and heretics (NPC4 140), and says Cleo and Bergamot go "shopping" who
knows where (NPC4 143).

**The Opener of the Door.** NPC4 25-27, 51, 53; NPC5 105; EV 234 (the Priestess waits
for "those who seek more"), NPC4 27 (Cresson waits for the next Opener). Doors that
won't open are the game's commonest event line (10, 15, 77, 81, 119, 121, 158, 169,
221, 238).

**Snakes.** EV 30/51 (the snake pillar, the only "cold-eyed" beast), 71 (the 2-Head
Snake), 105 (snakes of the ground), 184 (the snake door); Catalog 7:16 (holy places are
often ruled by snakes); the god is Quetzalcoatl, the feathered serpent (Enc.; Inferred
as the coffin's occupant). A motif, not a clue.

**DIMGUIL.** EV 0, 201, 205; SISETU 341; NPC1 289, NPC3 278, NPC4 14. The game's title
is the answer. (Outside knowledge: dingir is the Sumerian word for "god", so the god's
name is the word for god.)

**The Royal Guard.** EV 242 ("curse the Royal Guard"), SISETU 326 (the King sent the
Royal Guard after the tremor), 332 (the Guard's report from the altar). Keep the same
term.

**The Fortune Teller's topics** (SISETU 345-358 titles, 331-344 texts). The order
roughly follows the game:

| Topic | Text | Points to |
|---|---|---|
| The Beginning | 331 | the festival night |
| Priestess & Altar | 332 | S7; "truth or illusion?" |
| Old Friend | 333 | S6 (Inferred) |
| The Mask | 334 | S8, S41 |
| The Freezer | 335 | S12 |
| Strange Machine | 336 | S13 |
| Golden Warrior | 337 | S21, S47 |
| The Imprisoned | 338 | S24 |
| Ring Door | 339 | S33 |
| A Made God | 340 | S39 (Inferred) |
| The God's Name | 341 | S7, S45 |
| Strange Device | 342 | S49 |
| Dark God | 343 | S52 |
| The End | 344 | S53 |

## Translation traps

**Words a clue depends on.**

- **EV 105 and SISETU 339: sky and earth.** 105 has birds of the sky (天) and snakes that
  crawl the ground (地); the Fortune Teller says the large ring is the sky (大空) and the
  small ring the earth (大地). The current 105 says "birds of heaven" and "crawling
  snakes", so the English loses both halves of the mapping. Use "sky" and "ground" or
  "earth" in 105 to match 339.
- **Ring sizes.** 160-162 say small, middle, outer; SISETU 339 says large and small.
  Either make the Fortune Teller's large ring clearly the outer one, or call it outer.
  The NPCs say "discs" (円盤, as does 158); the Fortune Teller says "rings" (輪). Guy's
  "a disc split into three rings" (NPC1 288) bridges them. Keep both words recognizable
  as the same object.
- **Board 5.** "North is 0, south is 180" must stay numeric and in degrees; "red" must
  stay red; "vault" should match the Catalog's word for the Ruby Hand's treasure room.
- **Board 7 and the riddle.** GAME stays in glyphs. The riddle (94) must still describe
  a game, and "world" in "what do you call my world?" matters (the answer names the
  world, not the device).
- **SISETU 342.** The body says "strange machine" but the topic is "Strange Device", the
  dome is a "device" (EV 94), and "Strange Machine" is the lake machine's topic (350).
  The Japanese has the same slip. "Strange device" in 342 would point players at the
  right puzzle.
- **EV 17, 44, 45.** The paste must stay sticky and must be the same paste. Don't make
  17 a droppings joke.
- **Board 1 and the "forget" chain.** Board 1 now reads "Did you equip your gear?", which
  drops "forget" (the Japanese asks whether any equipment has been forgotten). EV 130
  ("don't forget full gear") and 225/226 ("Did we forget something?") pay it off at the
  small door.
- **EV 130 "full gear".** It must mean all your equipment, since the small door needs
  all four gold pieces.
- **EV 36 "burning gaze".** Keep the heat: it is the Fire Golem, and the Japanese is a
  pun.
- **"Square" holes.** Keep "square" wherever the Japanese says it (see Setups).
- **The glyph color codes.** In the ancient-letter lines, {ff30}4 marks exactly the
  words the player must type or use (DIMGUIL, STAFF, LABORATORY, WAREHOUSE, ENERGY,
  COCKPIT, the area letters A-E in Area X, the Priestess's Door profile), and {ff30}5
  marks the teaching words. Board 7's GAME has no color. Keep every color code as it
  is; the distinction may be a deliberate signal.
- **The LITHOGRAPH across files.** Event text: LITHOGRAPH OF SUN. NPC files: "Lithograph
  of the Sun" (NPC2 82), "the Sun tablet" (NPC3 68). The Japanese uses 石板 both for the
  LITHOGRAPH and for the keyboard's "small tablets", so NPC lines saying "tablet" (NPC2
  84, NPC3 278, NPC4 30-34) need to make clear which one they mean.
- **Priestess, Medium and the door.** The item is RING OF MEDIUM (fixed English); the
  door says Priestess's Door; the FAQ calls it the Medium's door. EV 298 ("The
  Priestess... offers you a ring. Obtained RING OF MEDIUM.") is the one line that ties
  them. Keep it explicit.
- **EV 234 "the gods' word".** The Japanese is 神の言葉 in a story about one god (the
  god whose name is asked in 201). "The god's word" is the safer reading.
- **EV 152 "It's him!".** やつ is "that one" or "that thing"; the bones re-forming are the
  fiend just beaten. "Him" suggests a person the party knows.
- **Jade and the JADE MASK.** Boards 3, 5, 7, 9 go to Jade (ジェイド); the mask is jade
  (翡翠). English now links them by accident. It probably does no harm, but a reviewer
  should know the link isn't in the Japanese.
- **Cross-file terms.** 迷宮 is "labyrinth" in 205, 224, 237 but "maze" in 311, 313 and
  in the NPC files. 神殿 is "the Shrine" here and in NPC text, "temple" in the Catalog
  English. 邪教徒 is "heretics" in NPC text and SISETU 340, "cultists" in most of the
  Catalog. Make each pair agree so players can connect Catalog hints to the dungeon.
- **"Beautiful woman"** in 191, 205, 234, 236 should be the same phrase (see Setups).
- **Stone and iron pairs** (100/101, 175/176, 210/211) must keep the contrast.
- **"Pillar."** 24-31, 48-51, 12-13 are pillars; 166, 168, 228 are "great/huge pillars"
  (巨大な柱), the same noun in all three.

**Places where a loose or joking reading would break something.**

- 17 read as a joke loses the birdlime puzzle.
- 105 smoothed into poetry ("fled sunwise", "wheeled east") loses the dial.
- Board 6 is terse on purpose, but "three combinations, three doors", "directions" and
  "the mask" all carry weight.
- Board 5 is a burglar's joke note and also the only statement of the angle convention.
- 94's riddle can be witty, but the reward must still be "fruitless" or empty, and the
  world must be "imagined", or GAME stops being the obvious answer.
- 36 and 61 undercut themselves ("nothing happens... or so it seems"): keep the joke,
  but they are also the only warning of two very hard fights.
- 102 in NPC1 (Lychee: it wasn't me, I only kicked a pebble) is a joke that works because
  the player caused the change (EV 224).

**Oddities in the Japanese.** Only one of these is a corroborated mistake (EV 258).
Everything else is what the text says, checked in the source, with no outside source
confirming it's an error. Don't "fix" those in the English on this list's say-so.

- **EV 258 (corroborated):** the stuck stone is green, then "the blue stone can't be
  removed", and the closing thought has a bare "7" where {ff30}2 belongs. The hollow
  texts come in sets of three (first look, with the LITHOGRAPH, without it): 256-258
  for the blue stone, 262-264 and 265-267 for the green. 258 is the blue set's third
  string, and its green twins 264 and 267 have the same wording with "green" in both
  places and a proper {ff30}2. So "green" in 258's first line is the slip, and the
  broken code is in the source data, not the dump. No outside source mentions it. The
  English copies the slip and drops the opening color code.
- **EV 289-292:** the four pillar stones drop from a monster that "came out of the
  statue", though the pillars are pillars everywhere else, and 12-13 call the pieces
  "the stones from the pillars".
- **EV 222:** only the gauntlets are said to open the small door; all four pieces are
  required.
- **EV 215 MEATING:** the glyphs spell M-E-A-T-I-N-G. MEETING is a guess at the intent,
  not established. It's a teaching word, and changing it would change which letters it
  teaches, so it stays as it is.
- **EV 231:** a typo in the thought (この for こと); the meaning, "is there something we
  left undone?", is clear.
- **EV 178 and 179** are identical. The FAQ says WAREHOUSE is on a statue's head; the
  text says a pillar's head.
- **EV 262-264 and 265-267** are two full sets for the green stone; why is not known.
- **EV 227** ("A bed?") lacks the quotation marks its siblings 46, 52, 54 have.
- **EV 73** ends with {ff18}, a code not documented elsewhere; what it prints is not
  known.
- **SISETU 342** calls the GAME device a "strange machine" (see above).
- **NPC2 261:** Balbo's はし can be bridge, ladder or edge; the English says "bridge",
  which happens to echo the BRIDGE glyph door (245). Not established that either is
  meant.
- **EV 286, 287, 303** are debug and trade-show leftovers.
