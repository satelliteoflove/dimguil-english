# zarilchat: Zaril's party chat table, checked in the emulator

Task: for each chat block 0-13 of Zaril's party (handler 4, MCARD `talk_zaril`
0x800d9b34, talk_state 0x28), the bottom-bar line and the spoken lines as the game shows
them, whether each block can be rolled, and whether this matches the script dump
(`rips/re/work/C/scripts.json`, handler 4, array base 984, stride 200) and bugs.md 2.10.
Investigation only: no changes to game data, translations or main.

Worktree: `../worktrees/zarilchat`, branch `wt/zarilchat`, from main 4a53dc4. Nothing
committed (everything here is under the ignored `rips/`).
Disc: built in the worktree from 4a53dc4, `rips/iso/dimguil-en.bin` md5
756d4fb02c5f2334932096ec4fae9517 (build log 0 ERROR). Not published, no suite round.

Status: done. Nothing running (PIDs 119107, 119109, 119439, 119441 all finished).

## Report 1

### Result

Every block plays exactly what the dump says, in dump order: the bar line, then each
`say` in turn. The table in bugs.md 2.10 ("Block / Bar line / Zaril / Fritillaria /
Gaura", the "now" column of the proposed fix) is right for every block it lists. [emu]

| Block | Bar line (5:N) | Lines shown, in order | Reached by |
|---|---|---|---|
| 0 | 98 asked if they had any news | 54 Zaril, 55 Fritillaria, 56 Gaura | roll |
| 1 | 99 told them everything we knew | 57 Zaril, 58 Fritillaria, 59 Gaura | 2nd Talk press only |
| 2 | 99 told them | 60 Zaril, 61 Fritillaria, 62 Gaura | roll |
| 3 | 101 asked about other parties | 63 Zaril, 64 Fritillaria, 65 Fritillaria, 66 Gaura | roll |
| 4 | 101 other parties | 67 Zaril, 68 Fritillaria, 69 Gaura | roll |
| 5 | 101 other parties | 70 Zaril, 71 Zaril, 72 Fritillaria, 73 Gaura | roll |
| 6 | 99 told them | 74 Zaril, 75 Fritillaria, 76 Gaura | roll |
| 7 | 102 asked something personal | 77 Zaril, 78 Fritillaria, 79 Gaura | roll |
| 8 | 102 personal | 80 Zaril, 81 Fritillaria, 82 Gaura | roll |
| 9 | 99 told them | 83 Zaril, 84 Fritillaria, 85 Gaura | roll |
| 10 | 102 personal | 86 Zaril, 87 Fritillaria, 88 Gaura | roll |
| 11 | 102 personal | 89 Zaril, 90 Fritillaria, 91 Gaura | roll |
| 12 | 100 asked them about themselves | 92 Zaril, 93 Fritillaria, 94 Gaura | roll |
| 13 | 98 news | 95 Zaril, 96 Fritillaria, 97 Gaura | roll |

The English on screen for each line is in `forced.log` (and `shots/results_*.json`).
The bar line stays up while the replies play (screenshots).

### The roll

- `rand_upto(n)` (MAIN 0x8001cb18) returns 0..n inclusive. Read in the disassembly: it
  sums n+1 carries of the new state, so 0..n+1, and loops back (0x8001cba0 `beq a2, t3`,
  t3 = n+1) when the sum is n+1. A Python copy of it instruction for instruction
  (`randsim.py`) over 200,000 chained calls of `rand_upto(13)` gave 0-13, each about 7.1%.
  [code] (From an arbitrary 32-bit state the first call can return values out of range,
  but every state the function itself leaves is in the safe form, so the game never
  sees that.)
- In the game, 150 Talk presses from different RNG seeds (`rollsample.py`, breakpoint
  just after the roll's jal, 0x800dab14) gave raw values 0-13, all of them, never more;
  1 came up 12 times and was rerolled every time; the final blocks were 0, 2-13, 9-16
  each. [emu]
- So on a chat from the roll, blocks 0 and 2-13 are 1/13 each (7.7%). Block 1 never
  comes from the roll.

### Branches around the chat [code, MCARD disassembly; the press count also emu]

- `talk_count` (0x80079be8) is zeroed when the talk starts (0x800da4e4) and goes up by
  one on every Talk press (0x800da740), before anything decides what the press does.
- Each press, once every member has met Zaril: first the sale (an empty pack slot,
  greet_flags 0x800799b0 bit 0, `rand_upto(1) == 0`, progress_bits > 0xd) → sale; else
  the patch's heal offer (j 0x800c5820) if someone needs it; else, if `talk_count == 2`,
  block 1; else the roll.
- So block 1 plays only when the second press reaches the chat. If the second press
  turns into a sale or a heal offer, block 1 is skipped for that meeting. With the sale's
  conditions all met, each press is a sale half the time.
- Talk is never used up: in the natural run the menu stayed 7 after five presses, which
  played blocks 0, 1, 5, 8, 4 (press 3 onwards rolls again). [emu]

### Other things seen

- The English of 5:57 and 5:60 (blocks 1 and 2, Zaril ".........And? So what?"), 5:83
  and 5:95 (blocks 9 and 13, "Sorry. Nothing new to tell.") and 5:88 and 5:91 (blocks
  10 and 11, Gaura's Samurai line) is identical on screen. Not checked whether the
  Japanese differs (bugs.md 2.10 implies it does for 95).
- The greeting in these runs was 5:0 "Don't know your faces..." (Zaril's
  `talk_flags` 0x10 wasn't set in the setup); it doesn't touch the chat.
- The talk_zaril chat array in the dump (site 800dab74) is the one the game runs at
  state 0x28: no difference anywhere.

### How it was run (RAM-write setup; say so if anyone reuses the numbers)

`zchat.py` (forced blocks), `rollsample.py` (natural roll), `randsim.py` (rand_upto copy).
- Base: `rips/states/npc_talkmode.state` (a real talk, made 2026-10-07 on an older build).
- Laid in from this build: MAIN's patch bytes the state lacked (784 bytes: every byte
  where the state differs from the new SLPS and the new SLPS differs from the clean one,
  plus every differing byte in the VWF block 0x80073900-0x80073d00, since the new VWF
  code reads its table at 0x800159bb and the old state's leftovers there hung the text);
  the file tables 0x80051760-0x80052700; MCARD.BIN at 0x800a1000. NPC_MES5.OBJ then loads
  from the disc: the copy in RAM (0x801a0400) matched the build's file byte for byte in
  every run.
- Talk switched to Zaril: talk_party 0x80079797 = 4, talk_block 0x80079bb4 = 4,
  talk_state/script status/pos = 0, 0x80079565/66 = 0, the state's pending message box
  0x80079a3e = 0, talk_count 0x80079be8 = 0. Every member: +0xc7 |= 4 (met Zaril) and
  +0xc7 bit 0 cleared (so greet_flags bit 0 is clear and no sale), status 0, HP = max.
- Forcing: the roll's `jal rand_upto` at MCARD 0x800dab0c (word 0x0c0072c6) was written
  as `addiu v0, zero, B` (0x2402000B); its delay slot and the store at 0x800dab14 are
  untouched, so the game itself stores B in talk_block. The jal was written back before
  the second Talk press, so block 1 came from the game's own `talk_count == 2` path in
  every run. Block 1 was never forced.
- Lines read with a breakpoint on text_expand (0x8001dfc0, a0 = index, callers returning
  to 0x800b8fd8 = op 2 `say`) and one on bar_print (MCARD 0x800b3c40, a2 = index,
  callers returning to 0x800b930c/0x800b9324 = op 7 `bar`), in execution order.

### Files

- `shots/sheet_blocks.png`: one shot per block 0-13 (bar line + first reply).
- `shots/forceNN_pP_bB_KK_IDX.png`: every page drawn in the forced runs (P = Talk press,
  B = block played, IDX = the 5:N just drawn; `_x` = no new line).
- `natural/`: the unforced five-press run. `forced.log`, `natural.log`,
  `rolls.jsonl`, `dump_984.txt` (the dump's table, for the diff).
