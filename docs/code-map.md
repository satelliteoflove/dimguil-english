# Code map

The layout of Wizardry: Dimguil's code (SLPS-02691 Rev 1), and how to work on it with the
tools in `scripts/re/`. This file is the map. What the code *does* is written up in
`engine-notes.md`, which stays the narrative home of findings.

Everything here is read from the original disc's files (`rips/clean/dimguil/`), not our
patched build. Where our `asm/` patches change code, see "Patch sites" below.

## Tools

- Ghidra 12.1.4 (`~/tools/ghidra/ghidra_12.1.4_PUBLIC`, SHA-256 checked against the
  release notes) with lab313ru's PSX loader, release 2026.10.03 built for 12.1.4 (no
  published checksum; the zip's SHA-256 is 32abacd9...916255). The loader parses the
  PS-X EXE, maps the PlayStation's hardware registers and applies PsyQ 4.3 library
  signatures, which label about 1,150 library functions (strcpy, rand, sprintf, GPU,
  CD, SPU, memory card).
- A JDK (Ghidra needs one, and the system has only a JRE): Temurin 21.0.12.1 in
  `~/tools/jdk/`, checksum verified against Adoptium's.
- `scripts/re/ghidra.py` drives it headless. It sets JAVA_HOME itself.

Timings on this machine (16 cores): a full build of one module takes 2.5 to 4 minutes,
and all eight run in about 8 minutes four at a time (`-j 4`; each JVM takes up to 3 GB).
A refresh (apply symbols, re-export) takes 12 to 40 seconds per module, and all eight
finish in about 40 seconds with `-j 8`.

## Modules

| Module | File | Size | Loads to | Loaded by | `resident_overlay` | Covers | Game functions | C lines | Coverage |
|---|---|---|---|---|---|---|---|---|---|
| MAIN | SLPS_026.91 | 434,176 | 0x8000f800 (code from 0x80010000) | BIOS | | Main loop, file loading, text printer and glyph layers, event box, encounter loading, RNG, party copies | 190 | 11,200 | 97% of 0x800114d8-0x80024bf0 |
| MAZE | MAZE.BIN | 323,520 | 0x800a1000-0x800effbf | load_file table 0 index 178 (game modes 1, 4) | 2 | The maze: movement, events, encounters, camp; also loaded at boot | 418 | 37,300 | 97% |
| BATTLE | BATTLE.BIN | 237,608 | 0x800a1000-0x800db027 | index 173 (mode 2) | 3 | Battle; runs on MAZE's tail | 404 | 27,800 | 87% |
| MCARD | MCARD.BIN | 243,287 | 0x800a1000-0x800dc656 | index 175 (modes 7, 9) | 5 | NPC talks (all of them, despite the name), memory card save/load, settings reset | 164 | 32,700 | 84% |
| JOUKA | JOUKA.BIN | 310,662 | 0x800a1000-0x800ecd85 | index 172 (mode 3) | 1 | The castle town: tavern, inn, shops, temple, training, Compendium and catalog | 286 | 33,700 | 97% |
| HAZURE | HAZURE.BIN | 123,391 | 0x800a1000-0x800bf1fe | index 174 (mode 5) | 4 | Edge of Town (outskirts): settings, name entry, save menu; runs on JOUKA's tail | 116 | 13,100 | 99% |
| CMAIN | CMAIN.BIN | 183,952 | 0x800a1000-0x800cde8f | by name, `load_overlay_by_name` | | Card battles | 353 | 24,700 | 92% |
| CMENU | CMENU.BIN | 134,232 | 0x800a1000-0x800c1c57 | by name (mode 6) | | Card game menus | 239 | 14,700 | 86% |

"Coverage" is the share of the module's bytes inside a function; the rest is data
(strings, talk scripts, layout structs, handler tables). "C lines" counts the decompiled
output: 2,170 game functions and about 195,000 lines in all. The card game (CMAIN,
CMENU) is outside the rules-first analysis.

All seven overlays load at 0x800a1000, one at a time; checked against 23 RAM dumps,
where each dump matched exactly one overlay byte for byte. `load_file` (0x80012d18)
takes (destination, index, table). The card game overlays are the exception: they're
listed in table 0 (indexes 176 and 177), but the game loads them by name
(`\CMAIN.BIN;1`) through DsSearchFile and DsRead, so it reads the disc's directory
for them, not the table.

A smaller overlay leaves the tail of the one before it in RAM, and two overlays rely
on that (confirmed in the RAM dumps and by their calls):

- BATTLE runs over MAZE's tail. It calls seven MAZE routines between 0x800ee5f4 and
  0x800ef0cc, from about 40 places (0x800ef0cc alone has 26 callers). So a patch to
  MAZE in 0x800db028-0x800effbf changes battles too.
- HAZURE runs over JOUKA's tail. 0x800afa9c calls JOUKA's 0x800d9130.
- MCARD runs over MAZE's tail during a talk but calls nothing past its own end.

The build maps those tails into BATTLE's and HAZURE's programs as blocks
`UNDER_MAZE` and `UNDER_JOUKA`, so the calls resolve; the routines themselves are
exported with MAZE and JOUKA, and `xref.json` lists BATTLE and HAZURE among their
callers. In town, JOUKA leaves MAZE's last 0x3200 bytes in RAM, unused as far as known.

Memory, from the PSX loader's view of the executable: `.rdata` 0x80010000, `.text`
0x800114d8-0x8005155f (game code to 0x80024bf0, PsyQ library after), `.data`
0x80051560 (file tables at 0x80051760), `.sdata` 0x80079538, `.sbss` 0x800795b8,
`.bss` 0x80079c88-0x800a0baf. Then the overlay window, then buffers the game loads into:
NPC text 0x801a0400, monster records 0x801b0680 in battle, item names 0x801d1000,
FIGHTMSG 0x801d7000, SISETU 0x801d8c00, talk script 0x801ff118. main passes
0x801ffff0 to a setup call at boot (inferred: the stack or heap top). `$gp` is
0x80079538.

## How the build finds functions

`ghidra.py build` runs these steps for each overlay (MAIN gets steps 1 and 3 only):

1. Import the executable with the PSX loader and analyze it, with the overlay window
   unmapped. Mapping it first would let every call the executable makes into any overlay
   start a function in this one, and some land mid-function (0x800c76f0 cut Balbo's
   handler in two).
2. `LoadOverlay`: delete the placeholder functions those calls left in the window, map
   the overlay (and the underlay for BATTLE and HAZURE), seed functions at jal targets
   and `addiu sp,sp,-N` prologues that look like function starts, analyze.
3. `SeedOrphans` over MAIN's game code, with every overlay's jal targets, so all
   programs have the same MAIN functions.
4. `CleanOverlay`: drop functions that don't start like one, or ran into data, unless a
   call (or a jump from somewhere other than the code running straight into them)
   keeps them; then re-derive every function's body, since a junk entry cuts the real
   function around it short. Functions named in our CSVs are never dropped.
5. `SeedOrphans` over the overlay: every `jr ra` no function covers gets one.
6. `CleanOverlay` again, `RecordLibrary`, `ApplySymbols`, `ExportModule`.

What's left that isn't right: five functions decompile into bad data (BATTLE 0x800a1394,
CMAIN 0x800cd29c, 0x800cd6d8, 0x800cd7b8, CMENU 0x800c0b68). They're the executable's
calls meant for other overlays, and their files say `SUSPECT` at the top. Some real
functions have no reference at all (MAZE has about 80 small ones): they're reached
through pointers set up at run time, or they're dead code. A function's
`pointer_from` lists code that takes its address and data words that hold it
(`data:ADDR`), which is how BATTLE's 160-odd handlers in tables show up.

## The main loop

`main` (0x800114d8) boots (loads MAZE, sets `game_mode` 4), then loops forever:

- `game_mode` (0x8007967e) requests a switch. main loads the overlay that mode needs,
  sets `resident_overlay` and `game_state`, and clears `game_mode` to 0. The modes (which
  overlay each loads is read from the code; when each is used is inferred): 1
  MAZE (from town), 2 BATTLE, 3 JOUKA, 4 MAZE (at boot), 5 HAZURE, 6 card game, 7 MCARD,
  8 the catalog or Compendium screens (0x800e38fc or 0x800ea6c8, by 0x800796d2), then
  town, 9 a talk (MCARD, `talk_state` 0, portrait file from a name table at 0x8005e5c8).
- `game_state` (0x80079a13) picks the overlay routine main calls each frame: 1, 3, 5, 9,
  0x32, 0x33 and 0x35 at least. The maze loop's return value (0x800a2cd8 in MAZE) picks
  what happens next (2, 3, 4, 5, 7 are handled). Mapping each value is phase 2 work.
- In state 0x35 (talk), `talk_party` (0x80079797) picks one of 23 handlers in MCARD:
  0 Guy `talk_guy`, 1 Balbo `talk_balbo`, 2 Fontana `talk_fontana`, 3 0x800d65c8,
  4 0x800d9b34 (inferred: Cresson's and Zaril's parties), then 6-0x17 at 0x800bff60,
  0x800c064c, 0x800c08d0, 0x800c0b68, 0x800c12f4, 0x800ce4ec, 0x800cea7c, 0x800cebc8,
  0x800cee54, 0x800cf0dc, 0x800cf364, 0x800cf5f0, 0x800d5750, 0x800d5910, 0x800d5d2c,
  0x800d5f8c, 0x800d902c, 0x800d9334.

The executable calls into overlays at fixed addresses. Each call only makes sense with
the right overlay resident, so in each module's program some of MAIN's calls into the
window point at data or at the middle of a function. The build ignores those: it
analyzes MAIN with the window unmapped first, and only seeds functions there that look
like starts.

## Known entry points and tables

The named symbols are in `scripts/re/symbols/seed.csv` (131 so far, every address in
engine-notes, cheats, the asm patches and the scripts). The main ones:

- MAIN: `main`, `load_file`, `load_file_alt` (encounter path), `load_overlay_by_name`,
  `rand_upto` (0..n inclusive), `text_expand`, `text_read_code`, `event_box_open`,
  `event_box_print`, `glyph_*` (sprite layers), `encounter_load`, `party_copy_build`.
- MCARD: the talk handlers above; `talk_script_run` (0x800b8ccc) and `talk_opcodes`
  (0x800a1cc4, labels `talk_op*`); the static talk scripts `talk_script_guy`,
  `talk_script_balbo`, `talk_script_fontana`; `yesno_read`, `bar_print`; the rescue
  scan and fee labels; memory card code at 0x800a9554-0x800aa9e0 (the functions there
  call the library's card routines).
- JOUKA: `town_text_layers`, the Compendium and catalog layouts, the temple screen
  (0x800c95f0, patched by temple_layout.asm), the shop captions (0x800bae4c, 0x800bb914,
  0x800bf9ec), the status screen (0x800cbddc), name entry (0x800af5d8, 0x800b3e24,
  0x800b843c).
- RAM: `roster` (Roster[20]), `parties` (PartyRec[20]), `current_party_id`, `cur_area`,
  `cur_x`, `cur_y`, `cur_facing`, `progress_bits`, `game_mode`, `game_state`,
  `talk_party`, `talk_state`, `config`, the seen bitfields, the card stock, the file tables.

`scripts/re/types.h` holds the record layouts (Roster, PartyRec). Typing a global makes
the decompiler print `roster[i].items[k] = 0xffff` instead of
`(&DAT_8007d728)[i * 0x68 + k] = 0xffff`.

## Phase 2: suggested split

By subsystem, with what each owns. Sizes are decompiled C lines; the biggest functions
are state machines and read slowly.

| Subsystem | Owns | Size | Start from |
|---|---|---|---|
| A. Maze: movement, events, encounters | MAZE, apart from the camp; the encounter roll and how a friendly NPC meeting starts (handing off to mode 9); event triggers and their flags; what a wipe does | ~25,000 | the maze loop 0x800a2cd8 and its return codes; `encounter_load` callers; MAZE's biggest functions (0x800d0514, 0x800bb790, 0x800daa1c) |
| B. Camp and maze menus | MAZE's camp: spells and items used outside battle, the party menus, settings | ~12,000 | `camp_config_toggles` 0x800d9304; MAZE functions not claimed by A |
| C. NPC talks | MCARD 0x800b0000 up: all 23 handlers, the script interpreter and opcodes, the scripts as data (a script dumper would help), which lines play when (`progress_bits`, `met_bits`) | ~28,000 | `talk_script_run`, `talk_balbo` (calibrated), `talk_party` |
| D. Battle | BATTLE: turn order, attacks, spells, status effects, rewards, fleeing, NPC parties as enemies; the MAZE routines it calls (0x800ee5f4-0x800ef0cc) | 27,700 | main's calls into BATTLE per game state |
| E. Town | JOUKA: tavern, inn (aging, level-up?), Boltac's (buy, sell, identify, uncurse), temple (raising: costs and odds), training grounds, Compendium and catalog | 33,700 | main's calls into JOUKA per game state; the patched screens listed above (temple 0x800c95f0, shops, status) |
| F. Edge of Town and save/load | HAZURE, and MCARD 0x800a1000-0x800b0000 (memory card, save format, settings) | ~17,000 | the memory card cluster 0x800a9554-0x800aa9e0; HAZURE's 0x800a4ef8, 0x800afa9c |
| G. Characters, items and records | Cross-cutting: owns `types.h`. Roster, party copies, party table, item and monster records, spell tables, class and race rules; MAIN's game functions not claimed by others | ~10,700 plus field use everywhere | `globals.json` readers and writers of `roster` and `parties`; `party_copy_build` |

A and C meet at the friendly encounter; C and F share MCARD; E and G both touch level-up
and aging. Whoever finds a routine first names it; the other reads the CSV.

## How to work

1. **Read** `rips/re/decomp/<MOD>/<addr>_<name>.c`. Each file starts with the module,
   address, name and size, its callers, any functions that take its address, and the
   symbol's note. `ghidra.py where ADDR` finds the function holding any address in any
   module. `rips/re/xref.json` has callers across modules (an overlay's calls into MAIN
   count), and `rips/re/globals.json` has every global's readers and writers.
2. **Name** what you learn in your own CSV, `scripts/re/symbols/<subsystem>.csv` (same
   columns as `seed.csv`: module, address, name, kind, confidence, source, note, type).
   Use MAIN for executable code, RAM for data outside the overlay window, and the
   overlay's name for anything inside it, since overlays share addresses. Mark each row
   `confirmed` (say how: code read, RAM watch, emulator test) or `inferred`. Struct
   fields go in `types.h`, with the same marks; keep the record sizes exact.
3. **Refresh** your module: `python3 scripts/re/ghidra.py refresh MAZE` (seconds), then
   re-read. `ghidra.py check` validates every CSV first: unknown modules or kinds,
   addresses outside the module, and the same address named two ways in one module.
   A full `build` is only needed if the analysis itself changes.
4. **Write it up** in `engine-notes.md`: what the code does, with addresses, each claim
   marked confirmed or inferred. Add the story of a hard trace to `writeup-notes.md`.

Parallel work is safe across modules. Each module is its own Ghidra project, and every
run takes a per-module lock (`rips/re/locks/`), so two analysts on the same module take
turns of seconds each. Each analyst writes only their own CSV, so there are no merge
conflicts. The one shared file is `types.h`: subsystem G owns it, and others propose
fields to G or add them carefully with the sizes checked.

A name removed from a CSV stays in the Ghidra program until the next full build.

## Reading the decompiled C

- Byte loop counters come out as `iVar = iVar + 1; ... iVar * 0x1000000 >> 0x18 < 10`:
  the compiler kept the counter in a sign-extended byte. Read it as `for (i = 0; i < 10; i++)`.
- Talk handlers build their scripts on the stack, so their first few hundred lines are
  `local_xxxx = 0x6d;` stores. The static scripts in MCARD's data are easier to read
  from the data than from the C.
- Globals reached through `$gp` (0x80079538) resolve to addresses: `rand_upto`'s
  `0x20($gp)` shows as `DAT_80079558`.
- In the big state machines, the state variable (`talk_state` and the like) is compared
  in long if/else chains, not a switch. Search for the state value.
- Calibration (2026-10-11): `talk_balbo`'s offer scan and fee loop, already traced
  from the disassembly on 2026-10-10, read the same in C. With `roster` and `parties`
  typed, the fee loop is near-source:

  ```c
  iVar17 = (int)parties[(char)rescue_candidates[rescue_candidate_count]].members[(char)iVar10];
  if (iVar17 != -1) {
    roster[iVar17].area = 0xff;
    ... roster[iVar17].items[cVar7] = 0xffff;
        roster[iVar17].item_state[cVar7] = 0xff;
  ```

  The C also turned up a ladder on `progress_bits` (6, 0xe, 0x1e, 0x3e ... 0x1fe), which
  supports reading it as story progress bits.

## Patch sites

Our patches change code in these functions (generated by `scripts/re/patchsites.py`,
which reads the `.org` lines in `asm/*.asm`; data-only patches, the card game strings,
the battle name fixes and the settings name tables, are left out). Regenerate after a
build if function boundaries change. The decompiled C shows the original; read the patch before trusting it
at these spots.

| Module | Function (patched addresses) | Patch |
|---|---|---|
| MAIN | FUN_80012a4c (0x80012c88) | english_defaults.asm |
| MAIN | FUN_8001e1f0 (0x8001e2fc, 0x8001e370) | word_wrap.asm |
| MAIN | FUN_8001f9d8 (0x8001f9d8) | vwf.asm |
| MAIN | FUN_8001fb4c (0x8001fc18, 0x8001fc1c, 0x8001fc80, 0x8001fca4, 0x8001fcac) | vwf.asm |
| MAIN | FUN_8002027c (0x8002027c) | vwf.asm |
| MAIN | FUN_80022024 (0x80022048, 0x8002204c, 0x800220b4, 0x800220d8) | vwf.asm |
| MAIN | FUN_80023e98 (0x80023f68) | english_defaults.asm |
| MAIN | event_box_open (0x80021bfc) | event_window_pool.asm |
| MAIN | event_box_print (0x8001ffe8, 0x80020170, 0x80020174, 0x800201d8, 0x800201fc, 0x80020204, 0x80020274) | voicing_marks.asm, vwf.asm |
| MAIN | text_expand (0x8001e19c) | word_wrap.asm |
| MAZE | FUN_800a1ecc (0x800a1f9c, 0x800a1fc0) | vwf.asm |
| MAZE | FUN_800ba48c (0x800bab9c) | return_prompt_icon.asm |
| MAZE | FUN_800bed7c (0x800bef6c) | training_sign_pool.asm |
| MAZE | FUN_800d9304 (0x800d9cd8) | english_only.asm |
| MAZE | voicing_merge (0x800a3134) | voicing_marks.asm |
| BATTLE | FUN_800d202c (0x800d2038, 0x800d2150, 0x800d21d0, 0x800d21ec) | vwf.asm |
| BATTLE | FUN_800d3100 (0x800d3120) | vwf.asm |
| BATTLE | voicing_merge (0x800d3510) | voicing_marks.asm |
| MCARD | FUN_800aa9e0 (0x800aae88) | english_only.asm |
| MCARD | FUN_800ac8d0 (0x800acbb4) | english_only.asm |
| MCARD | FUN_800ad018 (0x800ad250) | english_only.asm |
| MCARD | FUN_800ad524 (0x800ad638, 0x800ad65c) | vwf.asm |
| MCARD | voicing_merge (0x800ae4e4) | voicing_marks.asm |
| JOUKA | FUN_800a2198 (0x800a348c) | town_text_pool.asm |
| JOUKA | FUN_800af5d8 (0x800af8b0) | name_entry_latin.asm |
| JOUKA | FUN_800b3e24 (0x800b4560) | name_entry_latin.asm |
| JOUKA | FUN_800b843c (0x800b8558) | name_entry_latin.asm |
| JOUKA | FUN_800bae4c (0x800bb0a0) | shop_caption_layer.asm |
| JOUKA | FUN_800bb914 (0x800bbca4) | shop_caption_layer.asm |
| JOUKA | FUN_800bf9ec (0x800c0d78) | shop_caption_layer.asm |
| JOUKA | FUN_800c95f0 (0x800ca9b8, 0x800caa08, 0x800caa30, 0x800caa5c) | temple_layout.asm |
| JOUKA | FUN_800cbddc (0x800cbec0) | status_text_pool.asm |
| JOUKA | FUN_800dbd7c (0x800dbe4c, 0x800dbe70) | vwf.asm |
| JOUKA | FUN_800dd5a8 (0x800deb1c) | catalog_tall_text.asm |
| JOUKA | FUN_800e31b8 (0x800e33bc, 0x800e33c4, 0x800e340c) | catalog_vwf.asm |
| JOUKA | voicing_merge (0x800dc76c) | voicing_marks.asm |
| HAZURE | FUN_800abbd4 (0x800ac5c8) | english_only.asm |
| HAZURE | FUN_800ac9f4 (0x800ace48) | name_entry_latin.asm |
| HAZURE | FUN_800ae990 (0x800aeab8) | name_entry_latin.asm |
| HAZURE | FUN_800bc99c (0x800bca6c, 0x800bca90) | vwf.asm |
| HAZURE | voicing_merge (0x800bd2f8) | voicing_marks.asm |
| CMAIN | FUN_800aa850 (0x800aa88c) | english_only.asm |
| CMAIN | FUN_800b5330 (0x800b5508) | cb_strings.asm |
| CMAIN | card_config_screen (0x800aa94c) | english_only.asm |
| CMENU | voicing_merge (0x800be944) | voicing_marks.asm |
