# Fewer languages and toolchains: ideas (2026-10-16)

Not a plan yet; written for Chris to choose from.

## What's in the repo now

| Piece | Language / toolchain | Size | Needed for |
|---|---|---|---|
| Text dump and encode, byte patches (`src/`) | Kotlin, built by Gradle on a JDK 21 | ~900 lines, 22 files, plus `gradlew`, the wrapper jar and two `.kts` files | every build |
| Tools, fit checks, name fixes, harness, emulator driver | Python | ~130 files | everything else |
| The game patch itself (`asm/`) | MIPS assembly, built by armips | 39 files | every build |
| Disc image | mkpsxiso (C++, built from a pinned commit) | external | every build |
| Glue (`build.sh`, `suite_round.sh`, `publish_test.sh` ...) | shell | 5 files | builds, rounds |
| Code analysis (`scripts/re/ghidra_scripts`) | Java, run inside Ghidra | 8 files | analysis only, never the build |
| NPC review tool page | JavaScript and HTML | 1 page | review sessions |
| Emulator debug hooks | a C patch to Beetle PSX | 1 patch | the harness |

Players never touch any of this: the release is a patch file. It only matters to whoever
builds the patch, which means Chris, the agents and any future contributor.

## Option 1: port the Kotlin tool to Python (recommended)

The Kotlin tool does four jobs: dump the Japanese script, encode the English with the
game's table (including the digraph compression), repack each file's sections and
pointers, and apply the `binary/*.json` byte patches. Python already does the neighboring
work: `gametext.py` decodes with the same table, and `namefixes.py` encodes glyphs.

- **Removes:** `src/`, `build.gradle.kts`, `settings.gradle.kts`, `gradle/`, `gradlew`,
  `gradlew.bat` and `gradle.properties`, plus the JDK and the Gradle download in CI
  (`release.yml`).
- **Leaves:** Python, MIPS assembly and two pinned external tools (armips, mkpsxiso).
- **Proof it's right:** this is the cheapest kind of port to check. Build with both
  encoders and compare every file in `rips/dirty`, then the disc's md5. A byte-identical
  disc needs no new suite round.
- **Effort:** one agent job of a few hours, mostly the compression and the pointer
  repacking, which have to match byte for byte.
- **Credit:** the tool is Remisse's (remii7/dimguil-patcher, GPL-3.0). A port is still
  derived from it, so the GPL stays and the credit stays in the README and release notes.

## Option 2: shell glue into Python

Five scripts. It would mean one language for all the glue, but shell is the natural fit
for "run these programs in order", and these rarely change. Low value; skip unless a
script grows logic.

## Option 3: Ghidra scripts into Python

Ghidra runs Python scripts too (PyGhidra). These scripts are analysis-only and run inside
a Java program anyway, so porting them removes no toolchain. Skip.

## Not worth touching

- **MIPS assembly:** it is the patch to the game's code.
- **JavaScript and HTML:** the review tool's page runs in a browser.
- **armips, mkpsxiso, the Beetle patch:** external, pinned tools with no Python equivalent
  worth writing.

## End state with option 1

Python for all our own code; assembly for the game patch; armips and mkpsxiso as pinned
external tools; Java only inside Ghidra, for analysis. A contributor's setup goes from
"JDK 21, Gradle, Python, armips, mkpsxiso" to "Python, armips, mkpsxiso".
