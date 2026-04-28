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
- If short on space, it may be possible to increase the size of some specific files by a little bit (e.g. EVENTMES 
is expandable by 1KB), but I haven't yet determined if it's completely safe to do so
- to place ellipses, use the placeholder char `\``
- use `'` instead of `’`

There are instances where text cuts off randomly if certain strings are too long. The cutoff point is not exactly 
deterministic and needs to be figured out on a case-by-case basis. Known instances:

- Boltac's Trading Post: tooltips get truncated earlier the longer the shop name is
- Spell descriptions: truncated past the 40th or so character when viewing spells at the Edge of Town
- Book of Reincarnation: 'Throb of the Demon's Heart' cuts off after viewing spells at the Edge of Town
- Narrator lines (EVENTMES): random cutoff point. One very long string might get printed in its entirety, while 
another of the same length might get truncated
