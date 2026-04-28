# dimguil-patcher

Tool for dumping the text of Wizardry Dimguil in a readable format and for patching it back. Also 
included is a series of ASM hacks to add partial VWF support to the game (which is required for 
the optional compression method to work correctly).  

The patcher works fine and could be considered feature-complete. The VWF hacks cover almost 
every text routine that uses the "large font" except for monster and item descriptions and quite
possibly some more stuff that I haven't personally encountered during my short-lived playthrough. 
I'm no longer working on this, though, so somebody else will have to pick up the torch.

Check out `Findings.md` for a random list of notes. There's a 99% chance I have forgotten some 
important details, so uhhh yeah.

The `translations` folder contains all the work that has been done so far by the translation  
team, uploaded with their permission. Thanks to [name removed] for translating and to [name removed] for
editing!

### Status

- `EVENTMES.BIN` 100% translated, ~15% edited
- `STATUS.OBJ` should be 100% translated, 0% edited
- `SISETU.OBJ` ~80% translated, 0% edited
- `FIGHTMSG.OBJ` 70-75% translated, 0% edited 
- `I_NAME_E.OBJ` was already in English, but various names have been relocalized
- `M_CATALG.DAT` various names have been relocalized, 0% of descriptions translated

Everything else is left untranslated. Anything past the first in-game area has not been 
playtested.

### Prerequisites

The instructions below assume you're using Linux, as that's what I've developed and tested the 
project on.

You'll need to download the following:

- Ripper55555's fork of [psximager](https://github.com/Ripper55555/psximager/releases) (`psxrip.exe` and `psxbuild.exe`)
- [armips](https://github.com/Kingcom/armips/releases/tag/v0.11.0)
- [Tim2View](https://github.com/lab313ru/tim2view/releases/tag/r90)
- JRE 21+
- Wine
- `dimguil-patcher.zip` from Releases

### Setup

1. Extract `dimguil-patcher.zip` (this will create a folder named `dimguil-patcher`)
2. Unpack your Dimguil image to a folder named `clean` (md5 of track 1: 9eeb5c508abb23c0e3538108b7755890):
```sh
$ wine psxrip.exe -v "<path-to-dimguil-image>.cue" clean
```
3. Make a copy of the `clean` folder and name it `dirty`, then move both to
`dimguil-patcher/rips`
4. Launch Tim2View and import `dimguil-patcher/SYSCG_000001_04b_01c.png` (the edited font 
sheet) into `dimguil-patcher/rips/dirty/dimguil/DATA00/SYSCG.BIN`
5. Move `psxbuild.exe` and `armips.exe` to `dimguil-patcher/tools`

### Using the tool

Dumping all known text to `out/dumps` (see `sections.json`):

```sh
$ java -jar dimguil-patcher.jar dump
```

Encoding the translated strings from the `translations` folder, copying them
to `rips/dirty` and finally rebuilding the image:
```sh
$ java -jar dimguil-patcher.jar encode-all && ./rebuild.sh
```

You'll find the new image in `rips/dirty`.  
>If you're getting errors like `Cannot open system area file "dimguil.sys"`, make sure you're
executing `rebuild.sh` from within `dimguil-patcher`.

Encoding a single string from CLI:
```sh
$ java -jar dimguil-patcher.jar encode-string "<string>" [-compress] 
```

### Notes on VWF and compression

The compression algorithm I've implemented scans the text for specific pairs of letters and encodes 
them to a single byte. For text to look correct in-game, my VWF patches and the edited font 
sheet need to be applied. Additionally, if you need to add/edit any digraphs, you'll have to make sure 
that the font sheet, the digraph table in `tables/compression.tbl` and the VWF LUT in `vwf.asm` are
all synced.
