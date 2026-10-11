# C. NPC talks (MCARD.BIN)

What the code does when you meet another party in the maze: who talks, which lines play
and when, and what the NPC parties' services do. This is analyst C's part of the
rules-first code analysis (see `docs/code-map.md`). Addresses are RAM; MCARD loads at
0x800a1000. Names are in `scripts/re/symbols/talk.csv` (and the older ones in
`seed.csv`). The line-by-line map of every NPC_MES string is in `docs/re/C-talk-lines.md`.

Every claim is marked:
- **[code]**: confirmed by reading the decompiled code or the disassembly
- **[dump]**: confirmed by running the handler's own code over a RAM dump with
  `scripts/re/talkscripts.py` (a MIPS interpreter; see "How it was traced")
- **[ram]**: read from a RAM dump of real play (no RAM writes)
- **[inferred]**: not confirmed

Nothing here was checked in the emulator yet. No RAM writes were used anywhere.

Who owns what: the maze decides when a talk starts and which handler runs (analyst A).
Roster field names are G's (`types.h`). Flag words named by others are used under
their names: `oneshot_flags` 0x80079b28 and `story_flags` 0x80079b44 (E), `camp_char`
0x80079a5a (B; the talk code uses it as "the member being worked on").

## Contents

1. Dispatch: which handler runs
2. The script interpreter and its opcodes
3. Characters, portraits and the met bits
4. The party handlers' state machine
5. Services: healing, NPC Kadorto, selling, rescue, fights
6. Each party: greetings, introductions, chat, farewells
7. The scene handlers (6-28)
8. Bugs and dead content
9. How it was traced
10. Translation impact

## 1. Dispatch

main's game state 0x35 is a talk. Each frame it calls one handler, picked by
`talk_party` (0x80079797). [code] The maze picks the handler and sets
`DAT_80079a90` to 9 (talk) or 2 (battle) in MAZE 0x800b4e94; 0x800abe44 copies that to
`game_mode` (A's area). [code]

| talk_party | Handler | Text file | What it is |
|---|---|---|---|
| 0 | `talk_guy` 0x800b5694 | NPC_MES1 | Guy's party, full menu |
| 1 | `talk_balbo` 0x800c7264 | NPC_MES2 | Balbo's party, full menu |
| 2 | `talk_fontana` 0x800cf8c0 | NPC_MES3 | Fontana's party, full menu |
| 3 | `talk_cresson` 0x800d65c8 | NPC_MES4 | Cresson, Cleo and Bergamot (the archive scholars), full menu |
| 4 | `talk_zaril` 0x800d9b34 | NPC_MES5 | Zaril, Fritillaria and Gaura, full menu |
| 6-10 | 0x800bff60, 0x800c064c, 0x800c08d0, 0x800c0b68, 0x800c12f4 | NPC_MES1 | Guy scenes |
| 11-17 | 0x800ce4ec, 0x800cea7c, 0x800cebc8, 0x800cee54, 0x800cf0dc, 0x800cf364, 0x800cf5f0 | NPC_MES2 | Balbo scenes |
| 18-21 | 0x800d5750, 0x800d5910, 0x800d5d2c, 0x800d5f8c | NPC_MES3 | Fontana scenes |
| 22-25 | 0x800d902c, 0x800d9334, 0x800d9558, 0x800d97e4 | NPC_MES4 | Cresson scenes |
| 26-28 | 0x800dbdd4, 0x800dc114, 0x800dc2d8 | NPC_MES5 | the mysterious man, Agan, Zaril's party attacked |

There's no handler 5. [code] Each handler sets `DAT_800796bf` (text file: table-2 index
0x33-0x37 = NPC_MES1-5) and calls `talk_load` 0x800bfe4c, which loads the text and, for
the five party handlers, runs that party's greeting selector. [code]

How a talk ends: the handler sets `talk_state` (0x8007981c) negative. -1, -3, -4 and -5
end the talk and main reloads MAZE (0xb2). -2 starts a battle (FUN_800c59bc, then
0x80020e10) with the NPT file numbered by `encounter_id` 0x800797f4 (A's name). [code] What the
maze does with -3 and -4 (Balbo's switch puzzle answers yes and no) is A's.

## 2. The script interpreter

`talk_script_run` 0x800b8ccc runs one script block: halfwords, an opcode then its
arguments, from `talk_script_pos` (0x80079a26). It returns each frame; when the block
ends, `talk_script_status` (0x800798a4) is -1. [code] The handlers build their scripts
on their own stack every frame, from constant stores, copies out of MCARD's data and
builder functions (`talk_script_builder` 0x800c154c, `talk_chat_builder` 0x800c2564,
`talk_farewell_builder` 0x800c7128), with a few slots filled from globals. [code] A
handler runs block N of an array as `base + talk_block * stride`, with `talk_block`
0x80079bb4. [code]

| Op | Args | What it does |
|---|---|---|
| -1 | 0 | End of block. [code] |
| 0 | 2: char, x | `show`: fades character `char`'s portrait in at x (FUN_800b49dc). While `talk_state` is 0x23 (introductions) it also sets met bit `char` in each member's `met_bits`. [code] Engine-notes had it as a "set met" op with one argument; it takes two, and the met bit is only set during introductions. |
| 1 | 2: char, x | `hide`: fades the portrait out (FUN_800b4c88); status 10. [code] |
| 2 | 1 or 3 | `say N`: prints NPC string N in the message box (`text_expand`). `say -2, m, N` puts roster member m's name in for {ff12}; `say -3, v, N` puts the number v in for {ff11}. [code] |
| 3 | 3: char, expr, x | `face`: sets the portrait's expression (FUN_800b4f44); status 15. [code] |
| 4 | 0 | End of block (the greeting arrays use it; same handler as -1). [code] |
| 5 | 0 | `close`: ends the talk (`talk_state` = -1) and closes the window (FUN_800b21f0) unless `talk_party` is 0x19 or 0x1c. [code] |
| 6 | 1: id | `load`: loads character id's portrait TIM into a free slot, then reloads the current NPC_MES file. [code] Engine-notes had 4 arguments; it's 1. |
| 7 | 1 or 3 | `bar N`: prints string N in the bottom bar (`bar_print(0xa6, 6, N, 1)`), with the same -2/-3 forms. Used for the topic log lines ("We asked them for healing.") and yes/no questions. [code] |
| 8 | 1: n | `gold n`: adds n to the first party member's gold, capped. [code] |
| 9 | 1: n | `cure n`: casts NPC cure n on `camp_char` (`npc_cure` 0x800b42d0; table below). [code] |
| 10 | 4: char, expr, x0, x1 | `slide`: moves a portrait from x0 to x1 over 24 frames. [code] |
| 11 | 1 or 3 | `say2 N`: like `say`, but sets 0x8007957e = 1, and the handler then shows it in the centered narration box (FUN_800bf94c). [code] |

Portrait x positions: 109 is the middle, 8 the left and 178 the right. [dump]

### NPC cures (`npc_cure` 0x800b42d0)

| n | Spell shown | Effect | |
|---|---|---|---|
| 0 | Dios | +2d4 HP if status < 0x80 | [code] |
| 1 | Dialko | clears status bit 0x20 (paralysis) | [code] |
| 2 | Dial | +2d8 HP if status < 0x80 | [code] |
| 3 | Latumofis | clears bit 4 (poison) and zeroes `poison` (+0x78) | [code] |
| 4 | Dialma (Balbo calls it "Madial", 2:122) | +3d8 HP if status < 0x80 | [code] |
| 5 | Madi | clears 0x64 (poison, paralysis, stone); full HP if the result is under 0x80 | [code] |
| 6 | Kadorto | clears 0x80 and 0x100 (dead, ashes) and sets HP to max | [code] |

HP gains are capped at max HP. [code] The status bit meanings (4 poison, 0x20 paralysis,
0x40 stone, 0x80 dead, 0x100 ashes, 0x200 lost) are from G's and E's docs and match
how these cures use them. [inferred]

## 3. Characters, portraits and the met bits

Portrait and character ids (portrait file NPC_nn.BIN is table-2 index id + 0x1f):
[code, dump]

| Id | Character | Id | Character |
|---|---|---|---|
| 0 | Guy | 10 | Zaril |
| 1 | Linaria | 11 | Artemisia |
| 2 | Alstron | 12 | Lilia |
| 3 | Lychee | 13 | Cephala |
| 4 | Balbo | 14 | Fritillaria |
| 5 | Alba | 15 | Cleo |
| 6 | Rosea | 16 | Bergamot |
| 7 | Reiran | 17 | Cresson |
| 8 | Gaura | 18, 19 | the mysterious man / Agan |
| 9 | Fontana | | |

Each character record has `met_bits` (+0xc6, 3 bytes) and `talk_flags` (+0xc9). Bit k of
`met_bits` is "has been introduced to character k" (byte k/8, bit k%8). The code
treats +0xc6..+0xca as one bit field: bits 20-23 and `talk_flags` (bits 24-31) are
per-NPC flags, and `marks[0]` (+0xca) holds two more. Below they're numbered as "flag n",
bit n of that field. [code] They're per character, not per party: a party
counts as having met someone if any member has the bit, though some checks need every
member. [code] F reports they're saved with the character, so first-meeting lines don't
replay after a reload.

Per-NPC flags found (all [code]):

| Bit | Set by | Read by |
|---|---|---|
| flag 20 (`met_bits[2]` & 0x10) | handler 9, giving Guy the Ruby Slippers | Guy's greeting (the 10,000 G thank-you) |
| flag 21 (`met_bits[2]` & 0x20) | handler 6 | |
| flag 23 (`met_bits[2]` & 0x80) | Guy's reward greeting | Guy's selector |
| flags 24-31 (`talk_flags` +0xc9, bit = flag - 24) | the selectors: Guy 24 and 29, Balbo 25 and 31, Fontana 26, Cresson 27 (0x08), Zaril 28 (0x10) | the same selectors |
| `marks[0]` 0x01 | Balbo's selector | Balbo's selector |
| `marks[0]` 0x02 | Cresson's 100% decipher check, and handler 22 | handler 22 only |

### Other words the talk code uses

| Address | Name | What it holds |
|---|---|---|
| 0x80079618 | `npc_stage` | Each party's story stage, one bit per stage: Guy bits 1-3, Balbo 4-6, Fontana 7-9, Cresson 10-12. A new game has 0x492, stage 1 for each. MAZE 0x800a45b0 moves them on as you first reach deeper areas, clearing the old bit as it sets the new one; handlers 20 and 25 move Fontana and Cresson. [code] |
| 0x8007986c | `progress_bits` | Bit k is set the first time you enter area tier k (MAZE 0x800a45b0): 1-4 tier 2, 5-8 tier 3, 0x12 tier 4, 0x13-0x16 tier 5, 0x17-0x1b tier 6, 0x1c-0x1f tier 7, 0x20-0x23 tier 8, 0x24-0x27 tier 9, 0x2b tier 10. So it grows 2, 6, 0xe, 0x1e ... 0x7fe. [code] |
| 0x80079b28 | `oneshot_flags` | Bits 10/11: Guy's party is Evil/Good. Bits 12/13: Balbo's party is Good/Evil. A new game has 0x2800: Guy Good, Balbo Evil. Bits 1-4: "the maze has changed" greetings seen (Guy, Balbo, Fontana, Cresson). [code; alignment meaning inferred from the strings] |
| 0x80079b44 | `story_flags` | Bit 10: the maze has changed (the metal walls), tested by every greeting selector. Bit 29: Cresson has handed over the decipher primer, which turns on camp's Decipher. [code] |
| 0x80079754 | `npc_flags` (A's) | Story bits for NPC meetings. Each scene handler sets its own bit, which A finds the maze uses to decide which NPC can turn up next (`npc_availability`). [code] |
| 0x8007e810 | current party | +1 member count, +2..+7 roster indexes, +0xe.. alignment per slot. [code] |
| 0x800799b0 | `greet_flags` | Bits the greeting selector builds for its decision. [code] |
| 0x80079b40 | `talk_speaker` | Which member speaks a greeting or farewell (random). [code] |
| 0x800795d6, 0x80079c6c, 0x800796d0 | `talk_str_a`, `talk_str_b`, `talk_topic_str` | String numbers filled into script slots at run time. [code] |
| 0x8007969a, 0x800796ed, 0x800796e4 | | Portrait and expression put into a greeting's second speaker slot. [code] |
| 0x80079b50 | `talk_menu` | Menu options: 7 means Talk/Fight/Leave and 5 means Talk/Leave. Bit 0 is cleared after a service (heal or three sales), which drops Fight. [code; what bit 0 means is inferred] |
| 0x80079be8 | `talk_count` | Talk presses this meeting (Cresson and Zaril only). [code] |
| 0x80079991 | `npc_sale_set` | Which sale set the next NPC sale uses. It persists between talks. [code] |
| 0x800a1cf8 | `npc_sale_table` | 54 sets of three items and a price, 8 bytes each. [code] |

Alignment class (Guy, Balbo and handler 11 work it out the same way, from each slot's
alignment): 0 is no Evil member, 1 is Evil and no Good, 2 is all three alignments, and
5 is Good and Evil without Neutral. [code] A party is "compatible" with Balbo when Balbo
is Good and the class is 0, or Balbo is Evil and the class is 1 or 2. For Guy it's Good
with class 0 or 3, or Evil with class 1 or 2. [code]

## 4. The party handlers' state machine

All five party handlers share one shape. The states are values of `talk_state`.
[code; Guy, Balbo, Fontana read in full, Cresson and Zaril read for the differences]

- **0**: load the text, run the greeting selector, which returns `talk_block`.
- **5**: play the greeting (an 80-byte-stride array).
- **10, 0xf, 0x14**: the menu. The cursor is 0x80079b8c.
- **0x19 → 0x1e "Talk"**: what happens depends on introductions to the leader.
  - If no member has been introduced, play the introductions (0x23). The block depends
    on alignment and stage, and opcode 0 sets the met bits.
  - If only some members have been introduced, play the re-introduction.
  - Otherwise, 50% of the time try a service, in order:
    1. a heal offer, when someone has status ≠ 0 or HP ≤ max/5, at 50% (state 0x2d)
    2. a sale, when some member has an empty pack slot and the party is compatible, at 50% (0x3c)
    3. a rescue, when a wiped party exists, at 50% (0x41)
  - If no service is chosen, play a chat topic (0x28).
- **Healing**: 0x2d offer, 0x32 pick a member, 0x37 result.
- **Sale**: 0x3c offer, 0x3d yes/no, 0x3e/0x3f the item picker (`npc_sale` 0x800b9898), 0x40 result.
- **Rescue**: 0x41 offer, 0x42 yes/no, 0x43 result.
- **Leave**: 0x55, then 0x5a picks the farewell, then 0x5f plays it.
- **Fight**: 99, 100 warning, 0x69 yes/no; yes means `talk_state` -2.

Picking the 50% branch and each service is `rand_upto(1) == 0`. So with nobody hurt and
no empty slot, a rescue is offered on 25% of Talk presses, when there's someone to
rescue. [code]

## 5. Services

### Healing

Every party offers healing (Zaril's doesn't). There are two healers per party, chosen
50/50 for each offer. [code] The offer comes in state 0x2d, you pick a member, and the
healer checks in order: healthy (full HP and status 0) gives a "doesn't need it" line
and lets you pick again. Then, for most healers, a 20% "out of magic" roll, then what
their stage lets them cure. [code] Nothing costs gold. [code]

| Healer | 20% fail first? | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|---|
| Guy (1:142-151) | yes, after the "can't treat status" check | Dios; any status: can't | Dialko, Dial; other status: can't | Dialko, Latumofis, Dialma; stone/dead: can't |
| Alstron (1:152-162) | yes | Dialko, Latumofis, Dialma; stone/dead: can't | Dialma; dead: can't | Kadorto (dead), Madi (HP) |
| Balbo (2:114-123) | yes | Dios; any status: can't | Dialko, Dial | Dialko, Latumofis, "Madial" (Dialma) |
| Rosea (2:124-135) | after the status checks | Dialko, Latumofis, Dial; dead: can't | Dialko, Latumofis, Dialma; dead: can't | Madi (poison/paralysis/stone), **Kadorto** (dead/ashes), Madi (HP; bug) |
| Artemisia (3:124-131) | yes | Dios, Dialko, Dial; others: can't (blocks 0-8) | | |
| Cephala (3:132-144) | yes | table shifted by one (bug) | | |
| Cleo (4:64-70) | yes | Madi for status, **Kadorto** for dead/ashes, Madi for HP | same | same |
| Bergamot (4:71-77) | yes | Madi; stone or dead: can't | Madi, **Kadorto**, Madi | |

All [code]. The stage bits are the healer's own party's (Guy bits 1-3, Balbo 4-6 and so
on); Cleo's and Bergamot's tables are in Cresson's handler, with Cresson's stages.
Fontana's party uses Cephala at stage 3 only. Details per block are in
C-talk-lines.md.

### NPC Kadorto always works

Cure 6 has no roll. It clears dead and ashes, sets HP to max, takes no gold, costs no
VIT and doesn't age the character. [code] It doesn't touch the lost bit 0x200. Five
characters cast it:

| Caster | Line | When it's offered |
|---|---|---|
| Rosea | 2:130 "Revival at the Temple has better odds... Are you sure you want me to do it here?" | Balbo's stage 3 (`npc_stage` bit 6, set the first time you reach areas 0x1c-0x1f). Her dead check comes before the 20% roll, so once she's picked it's certain. |
| Alstron | 1:158 "One can only hope it succeeds." | Guy's stage 3, after the 20% roll |
| Cephala | 3:139 "You don't want the Temple? Revival magic..." | by the shifted table, Fontana stage 2 with a dead member (see bugs) |
| Cleo | 4:67 "This isn't the Temple, you know. Are you sure that's all right?" | any stage, after the 20% roll |
| Bergamot | 4:74 "If it fails, there's no takin' it back." | Cresson's stage 2, after the 20% roll |

For comparison: the Temple revives the dead with 60 + 2×VIT out of 100, at 1 HP, else
they turn to ashes. Ashes come back with 68 + 2×VIT, else the character is lost. The fee
is taken before the roll (E, `docs/re/E-town.md`). Camp Kadorto works if rand(0..80)
< VIT×4, costs 0-1 VIT and ages the caster 1-52 weeks (B, `docs/re/B-camp.md`). So every
NPC warning that the Temple is safer is false in this code: the NPCs' Kadorto is free,
certain and complete. [code; not tested in the emulator]

Rosea's offer needs some luck to come up: on a Talk press with everyone introduced, 50%
services × 50% heal offer × 50% Rosea rather than Balbo, so 12.5%. Then you pick the dead
member. [code]

### Selling items

Guy's, Balbo's, Fontana's and Zaril's parties sell items; Cresson's doesn't (its state
0x3c is the decipher check). [code]

- **When**: some member has an empty pack slot, and the party is compatible
  (`greet_flags` bit 0), at 50%. Balbo and Fontana also need `progress_bits` & 4, so
  tier 2 reached. Zaril needs `progress_bits` > 0xd, so tier 3 reached. [code]
- **Which set**: picked on "yes" by `progress_bits`. These are the set ranges, both ends
  included (`rand_upto(n)` returns 0..n). [code]

  | progress_bits | Guy, Balbo | Fontana | Zaril |
  |---|---|---|---|
  | 2 | Guy only: 0-4 | (kept) | (kept) |
  | 6 | 0-8 | 0-8 | (kept) |
  | 0xe | 4-12 | 4-12 | 14-43 |
  | 0x1e | 9-16 | 9-16 | 14-43 |
  | 0x3e | 14-25 | 14-25 | 14-43 |
  | 0x7e | 18-34 | 18-34 | (kept) |
  | 0xfe | 27-43 | 27-43 | (kept) |
  | 0x1fe | 36-52 | 0-44 | (kept) |
  | > 0x3fd | 0-53 | 0-44 | (kept) |

  "(kept)" means `npc_sale_set` keeps whatever the last sale left there, possibly from
  another party. [code] The sets match exact values, so a `progress_bits` with a gap
  (if a tier can be skipped) would keep the old set. [inferred]
- **The sale** (`npc_sale` 0x800b9898): the set has three items and one price. The
  prices are 5, 200, 500, 1,000, 2,500, 5,000, 10,000 or 20,000 G, and cursed items are
  in the table. The price comes from the first member who can pay; if nobody can alone,
  the party's gold is pooled (FUN_800b1d34, FUN_800b1b90). The item goes to the first
  member with a free slot, with item_state 0 (5 for item subtypes 0x14/0x15). After
  three sales the menu's bit 0 is cleared. [code] The table itself is in
  `rips/re/work/C/saletable.json` (not tracked).

### Rescuing your wiped parties

Guy's, Balbo's and Fontana's handlers scan the party table. Cresson's and Zaril's have no
scan and no offer. [code; Cresson's and Zaril's read in full for this]

- **Candidates**: a party that's in use, isn't the current party, and whose members
  all have status > 0x1f. So paralyzed, stoned, dead, ashes or lost all count, not
  only dead. [code]
- **Offer**: `progress_bits` & 0x1e (true from tier 2 on; a new game is 2, so the
  first time you reach areas 1-4), at least one candidate, and the third 50% service
  roll. [code]
- **Yes**: one candidate party is picked at random (`rand_upto(count - 1)`). Each member
  gets `area` = 0xff (back in town), status unchanged, and pays the fee. [code]

| Party | Fee from each rescued member | |
|---|---|---|
| Guy | all gold | [code] |
| Balbo | every item: all ten slots emptied (0xffff, item_state 0xff) | [code] |
| Fontana | half the gold, and the items in slots 1, 3, 5, 7 and 9 | [code] |

These match `docs/engine-notes.md`. Rescued bodies don't get the "carried to the temple"
line (SISETU 614); they just turn up in the Temple's list (E). [code, E]

### Fights

Choosing Fight shows a warning (state 100), then a yes/no. Yes starts a battle with:
[code]

- Guy: NPT 0, 1 or 2 by stage; at stage 3, 3 once the maze has changed and 4 once
  `progress_bits` > 0x7fd
- Balbo: NPT 5, 7 or 8 by stage, or 9 at stage 3 once `progress_bits` > 0x7fd
- Fontana: NPT 10, 12 or 13 by stage
- Zaril: NPT 0xe
- Cleo and Bergamot: NPT 0xf (handler 25, forced)

The menu has Fight only while `talk_menu` is 7. [code] What the NPT files hold is D's
or G's.

### Cresson's decipher check

The archive scholars' Talk can play Cresson comparing your Decipher table with theirs
(4:84, 4:85). [code]

- **The match**: `decipher_score` 0x800d9ae4 counts the entries of `decipher_table`
  (0x80089b40) where the guess for ancient letter i is A-Z letter i. The match is
  count × 100 / 26, shown in 4:84 through {ff11}. So the right answer is the plain
  alphabet order. [code]
- **At 100%**: Cresson plays 4:85 ("You match us 100%... Thank you so very much") and
  sets `marks[0]` |= 2 on every party member. Nothing else reads that bit except
  handler 22, where it skips Cresson's speech about Cleo and Bergamot (see bugs). [code]
- **The primer**: the first Talk with the scholars, once everyone has been introduced
  and while `story_flags` bit 29 is clear, plays 4:162 (or 4:161 as "Robed man")
  "You'll need this item for your analysis. Do try using it in camp." It then sets
  `story_flags` bit 29, which is what turns on camp's Decipher command (B). No item is
  added to a pack: the "item" is the camp command. [code]

## 6. Each party

The greetings, introductions, chat topics and farewells, block by block, are in
C-talk-lines.md. The selectors' logic is summarized here. All [code] unless marked.

### Guy (handler 0, selector `greet_guy` 0x800b9ed0)

**Greeting flags:**
- 1: compatible
- 2: flag 20 (gave the Ruby Slippers)
- 4: flag 23 (got the reward)
- 8: flag 24 (first meeting done)
- 0x10: flag 29
- 0x20: met Guy
- 0x40: met Lilia
- 0x80: met Fritillaria
- 0x100: met characters 0-3
- 0x200: `oneshot_flags` bit 1
- 0x400/0x800: Guy Evil/Good
- 0x1000: the maze has changed
- 0x2000/0x4000/0x8000: stage 1/2/3

**Greeting blocks:**
- 0: Guy turned Evil (1:94).
- 2/3: the maze has changed.
- 4: **the reward.** Shown when the party gave the Ruby Slippers and has met Guy before,
  but hasn't had the reward yet (flags 20 and 24, not 23). It plays 1:104 "Thanks for
  bailing us out", then opcode 8 adds **10,000 G**, and it sets flag 23.
- 5/6: first meeting (Guy Good/Evil); sets flag 24.
- 7-36: random member greetings by compatibility and introductions.
- 37 and 40: Fritillaria and Lilia introduce themselves.
- 38, 39, 41 and 42 are never picked.

**Chat:** `rand_upto(11)` picks a topic, each with a block per stage (0-8 and 12-39).
The bottom-bar topic line is one of 1:281-285. Location and story topics (33, 40-44)
are kept 90% of the time; 9-11 never are (bug 8).

**Farewells:** built by FUN_800c7128.

### Balbo (handler 1, selector `greet_balbo` 0x800cbaa8)

**Greeting flags:**
- 1: compatible
- 2: flag 25
- 4: flag 31 (set with the "turned Good" greeting)
- 0x4000: `marks[0]` & 1
- 8/0x10/0x30: met characters 4-6, 4-7, 4-8
- 0x2000: met Artemisia
- 0x8000: met Balbo
- 0x40: `oneshot_flags` bit 2
- 0x80/0x100: Balbo Good/Evil
- 0x200: the maze has changed
- 0x400/0x800/0x1000: stage 1/2/3

**Greeting blocks:**
- 0 and 1: Balbo turned Good (2:92) and back to Evil (2:93).
- 2 and 3: the maze has changed.
- 4 and 5: first meeting, incompatible or compatible.
- The rest are random member greetings.

**Introductions:** blocks 0-2 (Balbo Evil) or 3-5 (Balbo Good), by stage. Re-introductions
are blocks 6-8 (2:108-113).

**Chat:** `rand_upto(11)` gives a topic pair, played by stage. In stage 3 there are also
location topics in areas 5-8, 0x13-0x16 and 0x1c-0x1f; each plays only while the
matching stone of the Tablet of the Sun (item 0x143's state bits 4, 0x20, 0x80) isn't
in.

**Farewells:**
- `talk_str_b` 21-25, or 26 for members who haven't met Balbo.
- Otherwise by alignment: 27-31 or 32.
- 33-46 name a dead member.

### Fontana (handler 2, selector `greet_fontana` 0x800d2f60)

**Greeting flags:**
- 1: flag 26
- 2: met Reiran
- 4: met Fontana
- 8: `oneshot_flags` bit 3
- 0x10: the maze has changed
- 0x20/0x40/0x80: stage 1/2/3

**Greeting blocks:**
- 0 and 1: the maze has changed.
- 2: first meeting.
- 3-9: not met Fontana.
- 10-16: met Fontana, using six member-variant functions.

**Chat:** `rand_upto(7)` gives a topic pair, played by stage. Stage 1 has its own
specials. Areas 0x20-0x23 add a location topic before the maze changes.

### The scholars (handler 3, selector `greet_cresson` 0x800d8210)

**Greeting flags:**
- 1: seen before (`talk_flags` 8)
- 2: met Cleo, Bergamot and Cresson
- 4: met Cresson
- 8: `oneshot_flags` bit 4
- 0x10: the maze has changed
- 0x20/0x40: Cresson stage 1/2

**Greeting blocks:**
- 0 and 1: the maze has changed (Cleo, nameless or named; sets `oneshot_flags` bit 4).
- 2: first visit, 4:0 "More visitors?" (sets `talk_flags` 8).
- 3: not introduced, 4:1.
- 4: Cleo alone.
- 5: Cleo plus Bergamot or Cresson, through two variant functions.
  - Bergamot's (0x800d85e8) checks:
    - whether every member is 50 or older (4:9)
    - whether someone knows every spell (4:10)
    - whether the Decipher table is untouched (4:11)
    - whether both Marguda (マルグダ) and Arabik (アラビク) are in the party (4:12)
    - a character with one exact stat line (4:13 names them)
  - Cresson's (0x800d8c98) checks:
    - a member named DIMGUIL (4:14, "the very name of so dreadful a god")
    - max HP > 9,999 (4:15)
    - level ≥ 100 for everyone (4:16)
    - otherwise 4:18
- 6 and 7: stage 2, Cresson alone (nameless or named).

[code; the Bergamot branch order is tangled in the decompile and is inferred in its
details]

**Talk:**
- The introductions (4 blocks) check Cleo, Bergamot and Cresson.
- The first Talk after that gives the primer (section 5).
- Then healing (Cleo or Bergamot), the decipher check at 50%, or a chat topic tied to
  `story_flags` bits 5 and 6 and `progress_bits`.
- At stage 1, on the second Talk press of a meeting, the chat is block 2 unless an
  earlier topic condition applies.

**Farewells:** `talk_str_b` 7 or 5 (stage 1), 0x9b or 0x9a (stage 2).

### Zaril (handler 4, selector `greet_zaril` 0x800db730)

**Greetings:**
- If no member has `talk_flags` & 0x10: block 0, 5:0 "Don't know your faces...". It
  sets the flag.
- If seen but not introduced to Zaril: block 1, 5:1.
- Otherwise a random speaker:
  - Zaril: block 4, 5:2.
  - Gaura: 5:123, or 5:18/19 once met.
  - Fritillaria: 5:122, or once met, through `greet_fritillaria` 0x800dba44:
    - 5:16 "the murder squad", if anyone has 10,000+ kills
    - 5:17 "the walkin' corpse", if anyone has died 10+ times
    - otherwise 5:13-15
- Blocks 2 and 3 are never picked.

[code]

**Talk:**
- Introductions: block 0 if nobody has met Zaril, block 1 if only some have.
- Then a sale (see above) or a chat topic: `rand_upto(13)`, rerolling 1. On the second
  Talk press of a meeting, the chat is always block 1 (5:99 + 57-59).
- There's no healing and no rescue.

[code]

**Farewells:**
- Not introduced to Gaura: 5:5-7 by speaker.
- Otherwise:
  - Zaril: 5:8 if a member is dead, naming them ("Hope the Kadorto takes"), else 5:9.
  - Gaura: 5:11 if a member is dead, naming them, else 5:10.
  - Fritillaria: 5:12.

[code]

## 7. The scene handlers

All [code]. "Met X" means some party member has met bit X.

| Handler | What plays | Branches | Sets |
|---|---|---|---|
| 6 (Guy) | Guy's party with Lychee's mishap, then the seal and tablet explanation (1:105-112) | greeting block by builder; explanation block by Guy's stage | met bits 0-3 for all; `npc_flags` bit 21; flag 21 |
| 7 (Guy) | statue warning, one line | met Guy: 1:88; not: **1:89** (bug, should be 1:87) | `npc_flags` bit 17 |
| 8 (Guy) | statue warning, one line | met Guy: 1:86; not: 1:295 | `npc_flags` bit 15 |
| 9 (Guy) | "you took down that big green brute", then 1:82 "Give the Ruby Slippers?" | met Guy 1:80, else 1:81. Yes with item 0x11e in a pack: 1:85, then say2 1:303 "The party suddenly vanished, leaving money lying at our feet." Yes without it: 1:84. No: 1:83 | `npc_flags` bit 15; on giving: removes the item, clears `npc_flags` bit 7, sets flag 20. **No gold here**: the money comes later as Guy's 10,000 G greeting |
| 10 (Guy) | "Just taking a breather", crazy trap ahead | met Guy: 1:91-93; not: 1:296, 89, 90 | `npc_flags` bit 8 |
| 11 (Balbo) | the two-switch door: "Wanna lend us a hand?" | same alignment (as Balbo's compatibility): 2:75-76, else 2:72; yes 2:73/77 (`talk_state` -3), no 2:74/78 (-4) | (the maze acts on -3/-4) |
| 12 (Balbo) | after the switches: 2:81 "ask me anything", then Balbo's full menu | none | `npc_flags` bit 19 |
| 13-17 (Balbo) | one line each: blue stone, center room, iron bars, three discs, treasure ahead | met Balbo: 2:83, 85, 87, 89, 264; not: 2:82, 84, 86, 88, 265 | `npc_flags` bits 16, 12, 10, 26, 4 |
| 18 (Fontana) | 3:74 "Are you searching for the Priestess too?", then Fontana's full menu | none | `npc_flags` bit 20 |
| 19 (Fontana) | the statue with a slot for the Tablet of the Sun | not met Fontana: 3:67; met: 3:68-71 (names the first member) | `npc_flags` bit 13 |
| 20 (Fontana) | the party splits up; Zaril leaves (3:76-89) | not met Fontana: 3:75 alone; met: the whole scene | `npc_flags` bit 11; `npc_stage` & ~0x1d0 \| 0x220: Fontana to stage 3 and Balbo to stage 2 |
| 21 (Fontana) | the pit trap: 3:90-92, then Fontana (3:93-94, or 3:97-98 if a member hasn't met him); then a rescuer | `npc_flags` bit 7 clear: Balbo 3:103-104 if met, else "Man in armor" 3:105-107. Bit 7 set: Guy 3:101-102 if met | `npc_flags` bit 3 |
| 22 (Cresson) | Cresson on Cleo and Bergamot (4:24-29), then his full menu | plays if `npc_flags` bit 2 is set and no member has `marks[0]` & 2; else straight to the menu | `marks[0]` \|= 2 for all |
| 23 (Cresson) | the little stone tablet with all 26 glyphs | met Cleo: 4:30-35; not: 4:36-41 | `npc_flags` bit 14 |
| 24 (Cresson) | Cleo reporting to the King | met Cleo: 4:42; not: 4:43 | `npc_flags` bit 24 |
| 25 (Cresson) | the control room: Cleo and Bergamot reveal themselves (4:45-54), then a battle | met Cleo: the reveal; not: 4:55 only | battle NPT 0xf; `npc_flags` bit 2; Cresson's stage 1 → 2 |
| 26 (NPC_MES5) | the mysterious man's warnings | `talk_script_status` on entry picks 5:105, 106, 107, or (4) the long speech 5:108-111; framed by 5:103/104 | `DAT_80079b48` \|= 0x80 |
| 27 | Agan, 5:112 | none | `npc_flags` bit 23 |
| 28 | Zaril's party attacked: 5:118-121 | none | ends with `talk_state` -5 |

## 8. Bugs and dead content

All found by code read. None has been seen in the emulator yet.

1. **Rosea's HP heal at stage 3 plays the wrong line.** Block 22 is say 2:135 "I see...
   Do take care." with cure 5 (Madi). The intended line is surely 2:134 (her Madi
   line, "All better now"), which no block uses. [code]
2. **Cephala's healing table is shifted by one.** Fontana's heal script array has no
   block for 3:134, but the code's block numbers from 11 up assume it's there (all but
   the cancel, 20). So:
   - Her 20% "out of magic" plays Dial (3:141) and heals.
   - At stage 1, stone or dead plays 3:135 "Paralysis" and casts Dialko.
   - Paralysis plays the poison line and Latumofis, so it isn't cured.
   - Poison gets Madi.
   - At stages 2 and 3, status plays "can't treat" (3:138).
   - Stage 2 dead gets Kadorto (3:139).
   - Stage 3 dead plays "no magic" (3:140).
   - HP heals land one block late.

   Artemisia's table is right. [code; the missing block is confirmed by the dumper,
   the off-by-one by reading the block numbers]
3. **Alstron's Madi (1:157) can't happen.** It needs `npc_stage` & 0xc == 0xc, Guy's
   stages 2 and 3 at once, and the maze always clears the old stage bit when it sets
   the next. [code] With it gone, a poisoned or paralyzed member at stages 2-3 falls
   through to the HP checks, and Alstron says they look fine if their HP is full.
4. **Handler 7 shows 1:89 to strangers.** Parties that haven't met Guy get 1:89 ("The
   room up ahead's got some crazy trap in it!", a line from handler 10) instead of
   1:87, the "Man with a greatsword" copy of the statue warning. Handler 8 uses the
   right pair (86/295), and every Balbo scene pairs n/n+1 the same way. 1:87 is never
   shown. [code: 0x800c0814 is `addiu a1, zero, 0x59` where the pattern needs 0x57]
5. **The pit (handler 21) never plays its middle block.** Block 1 (3:95-96, or
   3:99-100: "Heeey, what are you doing down there?" and "Looks like help has
   arrived") is never selected. The scene goes from "something's coming down from
   above" straight to the rescuer. And when `npc_flags` bit 7 is set but nobody has
   met Guy, no rescuer block is picked: block 0, the fall itself, plays again. [code;
   what bit 7 means is A's]
6. **Fritillaria names the wrong corpse.** 5:17 "Hey! It's {ff12}, the walkin'
   corpse!" should name the member who died 10+ times. The name loop searches for
   10,000+ kills instead, finds nobody, runs off the end of the party list (index 6)
   and copies the name of whoever byte 0x8007e818 points at. In every RAM dump we have,
   that byte is 0, so it's roster character 0. [code; the byte value is [ram]]
7. **The decipher reward skips a scene.** `marks[0]` bit 1 means two things: Cresson's
   100% decipher check sets it, and handler 22 uses it as "already heard Cresson's speech
   about Cleo and Bergamot". A party that finishes the Decipher table before the
   control-room battle never hears 4:24-29. [code; whether 100% is reachable before
   that battle is inferred]
8. **Some chat topics never play.** Guy's, Balbo's and Fontana's chat code first picks a
   special topic (by location, stage or story flag), then keeps it 90% of the time,
   but only if its block number is above the random range (`slti talk_block, 0xc` at
   0x800b6b28 for Guy and 0x800c9a20 for Balbo; `> 7` for Fontana). Specials with low
   block numbers are always thrown away and rerolled. [code]
   - Guy blocks 9-11 (1:195-210): the areas 1-4 and 0x17-0x1b topics.
   - Balbo blocks 6-8 (2:174-187), "about other parties", by stage.
   - Fontana blocks 6 and 7 (3:181-196), two of the stage-1 specials. Block 8
     (3:197-200) is never picked at all.
   - Balbo blocks 27 and 28 (2:243-247, 253, "heard that already") are never picked
     either.
9. **Cresson calls every party "boys".** His fallback greeting 4:18 "Well, boys, any
   progress?" is the only one of the three picked. 4:19 ("girls") and 4:20 ("my good
   fellows") are never used: the variant function only ever stores 0x12. [code]
10. **Never-picked greeting blocks**: Guy 38, 39, 41 and 42, and Zaril 2 and 3. [code]
11. **Cut services.** The text has an identify service that no code offers. Rosea
    (2:137-141), Cephala (3:145-150) and Cleo (4:78-83) have full "identify an item?"
    exchanges, with success, failure and curse outcomes, and every file has the log
    line "We asked them to identify items." Zaril has a whole healing table (5:35-42),
    but his handler has no heal offer. No handler stores any of these string numbers.
    [code]
12. **No re-introductions for Guy and Fontana.** Their handlers replay the full
    introductions whenever any member hasn't met the leader. Their "didn't we do this
    already?" lines (1:134-139, 3:117-123) and a second Guy line-up (1:128-133) never
    play. Balbo, Cresson and Zaril do have a partial-introduction branch. [code]

## 9. How it was traced

**Mapping the handlers.** main's game state 0x35 was followed to the `talk_party` switch.
Each handler was decompiled with Ghidra headless (`scripts/re/ghidra.py`) and folded for
reading with `scripts/re/cfold.py`, which collapses the inlined portrait loads and the
six-member loops the talk code repeats hundreds of times. Work copies are in
`rips/re/work/C/` (not tracked).

**Dumping the scripts.** The scripts don't exist as data: each handler builds them on its
stack every frame. `scripts/re/talkscripts.py` runs the handler's own code instead of
guessing.
- It's a small MIPS interpreter that loads `rips/probe/ram_talk94.bin` (a RAM dump taken
  during a talk with Guy) and maps the original MCARD.BIN (`rips/clean`) over the
  overlay window.
- It runs each handler from its entry until the first branch on the talk state. Every
  value loaded from a global the code writes is tagged, so slots filled at run time
  show as `{g:ADDR=value}`.
- It finds every `jal talk_script_run` and replays the few instructions before each
  one with `talk_block` 0 and 1, to get the array base and stride.
- It runs the builder functions separately, keeping a snapshot of each, because their
  arrays overlap.

`talkscripts.py --text` prints every block with the English of each string. `--json`
writes the lot for `talklines.py`.

**Conditions.** The conditions were read by hand from the decompiled C, checked against
the disassembly where the decompile was unclear (Balbo's reroll at 0x800c9a20, the
immediates in handler 7).

**Peers' docs.** The comparisons with the Temple and camp Kadorto use E's and B's
findings.

**Not done yet.** None of this has been run in the emulator. The best checks would be
watchpoints on `talk_block` and `camp_char` during a real heal offer, a RAM read of
`npc_sale_set` across a sale, and Rosea's Kadorto on a dead member in a natural save.

## 10. Translation impact

1. **The NPC Kadorto lines warn about a risk that doesn't exist in this code.** Five
   characters cast it (2:130, 1:158, 3:139, 4:67, 4:74), and it always works, for free,
   with no VIT or age cost. The Japanese lines carry the same warning, so translating
   them faithfully keeps the developers' irony (or oversight). Nothing to change; worth
   knowing for npc2-06's proposal on 2:130.
2. **Unused strings.** They needn't be polished first, and a reviewer shouldn't hunt
   for them in play:
   - 1:87, 1:157, 1:195-210
   - 2:134, 2:174-187, 2:243-247, 2:253
   - 3:95-96, 3:99-100, 3:181-200
   - 4:19, 4:20
   - the identify lines and Zaril's healing (bug 11), and the re-introductions (bug 12)
   - the never-picked greeting blocks

   C-talk-lines.md lists all 88 strings no script reaches.
3. **Context for lines that play in the wrong place.** These are worth a look:
   - 1:89 in handler 7
   - 2:135 after a Madi cast
   - Cephala's lines
   - 5:17's name

   A fix would be a code patch (one immediate each, for 1:89 and 2:135), not a text
   change. That's a decision for Chris.
4. **4:18 "Well, boys"** is shown to every party, mixed or all women. A neutral wording
   would fit what the code does.
5. **{ff12} and {ff11} slots.** These say lines insert a name or number:
   - 3:68 (the first member)
   - 4:13 (the stat-line character)
   - 4:84 (the match percentage)
   - 5:8, 5:11 and Balbo's 2:33-46 farewells (a dead member)
   - 5:17 (roster character 0, per the bug above)
6. **Gold in 1:303.** "Leaving money lying at our feet" isn't paid then. The 10,000 G
   comes with 1:104 on the next meeting. The line's wording is fine as long as it
   doesn't promise an amount.
