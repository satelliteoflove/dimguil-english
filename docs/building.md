# Building the patched image

You need Linux (or something close to it), a JRE 21+, Python 3 with Pillow,
[armips](https://github.com/Kingcom/armips) and
[mkpsxiso](https://github.com/Lameguy64/mkpsxiso) (which includes dumpsxiso). The
last two are easiest built from source.

You also need your own Rev 1 image. Track 1 should have the md5
`9eeb5c508abb23c0e3538108b7755890`.

Extract it once:

```sh
dumpsxiso -l -x rips/clean/dimguil -s rips/clean/dimguil.xml "<Rev 1 image>.cue"
```

Then build:

```sh
./scripts/build.sh
```

The patched image ends up at `rips/iso/dimguil-en.cue`. Set `ARMIPS` and `MKPSXISO`
if those tools aren't on your PATH. The header of `scripts/build.sh` walks through
the steps.

The committed translation files have the Japanese `source` text redacted, as they
were upstream. The build dumps the Japanese script from your own disc and puts it back
in a staging copy before encoding, so untranslated strings stay Japanese instead of
turning into "NA".

## Emulator tooling (optional)

You don't need any of this to build the patch. It's what we use to check text in the
real game boxes and to take screenshots without playing by hand.

`scripts/emu.py` is a small headless libretro frontend. It drives the Beetle PSX core
with no audio or video output: it boots a disc, steps frames with button presses, takes
screenshots, reads and writes RAM, and saves and loads states. It expects:

- the core at `~/src/beetle-psx-libretro/mednafen_psx_libretro.so` (or set
  `PSX_CORE`)
- a PlayStation BIOS, `scph5500.bin`, in `~/src/bios` (or set `PSX_SYSDIR`)
- Python 3 with Pillow, plus capstone for `scripts/mipsdis.py`

The core needs `scripts/beetle-dbg-hooks.patch`, which adds memory watchpoints,
breakpoints, an access log and code coverage (the `dbg_*` methods in `emu.py`). It was
made against libretro/beetle-psx-libretro commit `5718ab9b`:

```sh
git clone https://github.com/libretro/beetle-psx-libretro ~/src/beetle-psx-libretro
cd ~/src/beetle-psx-libretro
git checkout 5718ab9b829599687671503f11494ca6a0049c57
git apply /path/to/dimguil-english/scripts/beetle-dbg-hooks.patch
make -j
```

Most tools start from save states in `rips/states`. States hold RAM, including text the
game has already loaded, so states made before a rebuild show stale text. After a build
that changes text, run `scripts/mkstates.py` to make the standard ones again (boot,
town, tavern, party and each facility). A few others, like `maze_door.state` for the
dungeon text box and the battle states, were made by hand, and
need re-making after a build that moves files on the disc.

The tools:

- Fit checks, which need no emulator: `descfit.py` (item and catalog descriptions),
  `npcfit.py` (NPC dialogue), `evfit.py` (the event script), `fightfit.py` (battle
  messages).
- Rendering text in the real boxes: `npcshow.py` and `evshow.py` print NPC or event
  strings in the dungeon text box from `maze_door.state`; `battleshow.py` prints battle
  messages; `nptshow.py` starts a fight with an NPC party to show its names.
- Screenshots: `play.py` runs a button sequence from a state and screenshots each step;
  `explore.py` and `menushots.py` walk a facility's icon menu; `sheet.py` puts
  screenshots together into one image.
- Playtesting in DuckStation: `mktestsave.py` makes a memory card with a ready party
  (`rips/testsave.mcd`), `use_testsave.sh` swaps it into DuckStation's slot (and
  `--restore` puts your own card back), and `publish_test.sh` copies the build next to
  the Rev 1 image as `Wizardry - Dimguil (English WIP).cue`.
- Research: `gametext.py` decodes raw game text and maps disc files to the executable's
  load tables, `sjscan.py` and `relsearch.py` search binaries for text, `mipsdis.py`
  disassembles code from RAM, and `cardref.py` exports the card game's data.
