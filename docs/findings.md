# Remisse's findings

Remisse's notes from the original dimguil-patcher, kept as they wrote them. The notes
starting with "Since then" were added later, where things have changed. Newer engine
notes are in `engine-notes.md`.

- 0x89ac0  -> possibly the location where raw text is written, must investigate further
- 0x8b400  -> current string is loaded here
- 0x8b680  -> had f9 76 (encoded char)
- 0x1fed30 -> same as 8b400, but the string gets cut at \r; could be where the game ultimately reads the text from and submits it to the GPU
- 0x102c4  -> letter spacing
- exe
  - `FUN_8001dfc0` -> writes text into 0x8b400
  - `FUN_8001f4d4` -> probably renders chars with code < 0xd8

### Text files

- EVENTMES     -> narrator lines
- FIGHTMSG     -> combat
- I_NAME_E     -> item names (inventory)
- ITEM.DAT     -> item names + descriptions (compendium)
- ITEM_CA.DAT  -> item names (Boltac's?)
- M_CATALG     -> monster names & descriptions (compendium) 
- MESSAGE      -> card minigame
- NPC_MES1-5   -> lines of dialogue spoken by the various NPCs you encounter on the field
- SISETU       -> UI + fortune teller & king
- STATUS       -> UI

- ITEM_SE      -> unused? Possibly related to the trial version

All text regions are preceded by a header section.
Each header contains two bytes (offsets pointing to specific strings within the file).
Subtracting an header from the next one will give the length of the string referenced by the first header

### Control chars (not exhaustive)

- {ff21} (\n) -> line break
- {ff20} (\r) -> clears all text from the dialogue window
- {ff30}xx    -> sets the text color to xx
- {ff35}xx    -> converts letter xx to its equivalent ancient symbol
- {ff40}      -> string terminator

### Random guidelines and notes I wrote for the translation team

- Each string comes with a `length` field, that is, the number of bytes the original JP string needs. A good estimate 
as to the length you can aim at is `length * 1.5`. You can exceed that limit if it means delivering a better 
translation, but then you'd have to make sure that the game files do not end up bigger than the originals, meaning 
other strings will need to be shortened to recover that extra space
- You can expand some specific files past their original size by adding `"extendByBytes": <N>` at the top of their 
translation file, under the `file` field (e.g. `"extendByBytes": 1000` should probably be safe for EVENTMES), but I 
haven't yet determined if it's *completely* safe to do so (and you likely won't be able to create xdelta 
patches this way, so only do this if you have no other option)

> Since then: files can grow. `scripts/relocate.py` moves a file that outgrows its sectors
> to the end of the data track and updates the executable's file tables. The NPC dialogue
> files are now about 50 KB bigger each. The limits are each file's load buffer (only
> files with a known limit may grow) and the 16-bit string offsets, which cap a file at
> 64 KB; see `engine-notes.md`.

- to place ellipses, use the placeholder char `\`` (yeah, I know)
- use `'` instead of `’`

> Since then: the NPC dialogue files use three periods instead of the ellipsis placeholder.

- for ancient characters, write `{ancient_<x>}` (e.g. `{ancient_a}`) instead of `{ff35}xx` to achieve correct
spacing and to use 1 byte instead of 3 per char (see also `tables/codes.tbl`)

There are instances where text cuts off randomly if certain strings are too long. The cutoff point is not exactly 
deterministic and needs to be figured out on a case-by-case basis. Known instances:

- Boltac's Trading Post: tooltips get truncated earlier the longer the shop name is (rename to "Boltac's Shop" or
"Boltac's", idk)
- Spell descriptions: truncated past the 40th or so character when viewing spells at the Edge of Town
- Book of Reincarnation: 'Throb of the Demon's Heart' cuts off after viewing spells at the Edge of Town (worked around
this by renaming the book to "Tome{of}Rebirth" (notice the hacky `{of}` char))
- Narrator lines (EVENTMES): random cutoff point. One very long string might get printed in its entirety, while 
another of the same length might get truncated

> Since then: these haven't been rechecked one by one. The shop is still called Boltac's
> Trading Post, and SISETU still uses the `Tome{of}Rebirth` workaround.
