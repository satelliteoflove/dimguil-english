# Cheats and memory map

Codes found while building the test save (`scripts/mktestsave.py`). They're kept here so
they can become a downloadable cheat file (RetroArch `.cht`, DuckStation) later. Not
published yet.

All addresses are for **Rev 1** (SLPS-02691). They sit in the executable's data area,
which the translation patch doesn't move, so they should apply to both the Japanese
disc and the English patch. That's untested on the Japanese disc.

**Verified:** every value below was poked into RAM in the emulator (Beetle PSX) and
checked on screen, and the gold, seen and card values also survived a save and reload.
The codes haven't been entered as GameShark codes in RetroArch or DuckStation yet.

Code format: PlayStation GameShark `80aaaaaa vvvv` writes the 16-bit value `vvvv` to
`0x80aaaaaa`. RetroArch and DuckStation apply cheats every frame unless set to one-shot.

## Gold: 500,000 for a character

Gold is a u32 at roster record + 0x1c. Roster records start at `0x8007D708`, 0xd0 bytes
each, in the Training Hall's roster order (not party order). 500000 = `0x0007A120`.

Roster slot 1:
```
8007D724 A120
8007D726 0007
```
Roster slot 2:
```
8007D7F4 A120
8007D7F6 0007
```
Roster slot 3:
```
8007D8C4 A120
8007D8C6 0007
```
Roster slot 4:
```
8007D994 A120
8007D996 0007
```
Roster slot 5:
```
8007DA64 A120
8007DA66 0007
```
Roster slot 6:
```
8007DB34 A120
8007DB36 0007
```

## Catalog: every item seen

Boltac's catalog lists an item if it's in Boltac's stock (one byte per item from
`0x8008A0B0`) or its bit is set in a 40-byte bitfield at `0x8008A040`. This sets every
bit, so it may also list unused item slots.

```
8008A040 FFFF
8008A042 FFFF
8008A044 FFFF
8008A046 FFFF
8008A048 FFFF
8008A04A FFFF
8008A04C FFFF
8008A04E FFFF
8008A050 FFFF
8008A052 FFFF
8008A054 FFFF
8008A056 FFFF
8008A058 FFFF
8008A05A FFFF
8008A05C FFFF
8008A05E FFFF
8008A060 FFFF
8008A062 FFFF
8008A064 FFFF
8008A066 FFFF
```

## Monster Compendium: every monster seen

60-byte bitfield at `0x8008A068`.

```
8008A068 FFFF
8008A06A FFFF
8008A06C FFFF
8008A06E FFFF
8008A070 FFFF
8008A072 FFFF
8008A074 FFFF
8008A076 FFFF
8008A078 FFFF
8008A07A FFFF
8008A07C FFFF
8008A07E FFFF
8008A080 FFFF
8008A082 FFFF
8008A084 FFFF
8008A086 FFFF
8008A088 FFFF
8008A08A FFFF
8008A08C FFFF
8008A08E FFFF
8008A090 FFFF
8008A092 FFFF
8008A094 FFFF
8008A096 FFFF
8008A098 FFFF
8008A09A FFFF
8008A09C FFFF
8008A09E FFFF
8008A0A0 FFFF
8008A0A2 FFFF
```

## A Card in the first character's pack

Items are u16s at roster record + 0x20 (10 slots, `FFFF` = empty). Low 9 bits are the
item id, and the high bits are flags. `0x2000` was used here and the Card Master accepted it.
Item ids: 344 Card (`0x158`), 345 Almighty Card (`0x159`), 346 Change Card (`0x15A`).
This one writes a Card into roster slot 1, pack slot 10:

```
8007D73A 2158
```

Use this one-shot only. Left on, it puts a new Card back in the pack every time one is
registered, and it overwrites whatever is in that pack slot.

## Card battle: password registrations back to five

The counter under the password glyphs ("Left: N") is one byte. Five is the most the game
ever allows.

```
3008A262 0005
```

Verified as a RAM poke (the emulator test harness sets it before every password), not yet
as a cheat.

## Card battle: one of each Master and Option Card

The card stock, as the game's reset routine (near `0x80023ea0`) lays it out:

- `0x8008A268` 10 parties, 0xC bytes each
- `0x8008A2E0` 40 Unit Cards, 0x14 bytes each; first byte `0x80` + the unit's record
  number + 1, `0x80` alone is an empty slot
- `0x8008A600` 20 Master Cards, one byte each, the kind (0-5: Earth, Wind, Heaven,
  Mountain, Fire, Forest); `0xFF` is empty
- `0x8008A614` 30 Option Cards, 8 bytes each: kind (0-9: Weapon .. All-Stat), level (1-3),
  then Stat Growth % for HP, MP, Atk, Def, Magic, M.Defense; `0xFF` in the first byte is
  empty

All six Master Cards into the first six Master slots:

```
8008A600 0100
8008A602 0302
8008A604 0504
```

Option Cards need their level byte too, so one per line pair, e.g. a level 1 Weapon Card
in the first Option slot:

```
8008A614 0100
```

These overwrite whatever is in those slots. `scripts/mktestsave.py` writes the same
values (Option Cards 0-9 at level 1, growth 0) into the test save. Verified as RAM pokes
and on the Stock Card Details screen; not yet as cheats. Kinds 6 and up for Master
Cards, and 10 and up for Option Cards, show garbage.

## Other addresses (for reference, not cheats yet)

- Party copy of each character: starts at `0x80086880` (records seem to be 0x90 bytes
  apart, unconfirmed). It's rebuilt from the roster (exe routine at `0x80020bd0`), so
  poke the roster, not this.
- Roster record: +0x00 name (game encoding, `FF40`-terminated), +0x1c gold, +0x20 pack,
  +0x40 experience (u32), +0x44 looks like level / HP / max level / max HP (u16s),
  unconfirmed.
- The save menu is City Outskirts > Save Game. The save is named `BISLPS-02691PSWIZDIM` on
  the memory card.
