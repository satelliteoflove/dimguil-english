# Before and after

Screenshots of fixes, one folder per fix, kept for the writeup. `before.png` and
`after.png` are the main pair; other files are extra views of the same fix. The entry
in `writeup-notes.md` explains each one.

Only natural captures are kept: the screen as the game drew it after ordinary button
presses, from the test save or a save state. Shots made by writing text or code into
RAM, or from a state holding an older program, were left out. The status screen's
before is from Chris's own play-through state, shown at 2x.

| Folder | Fix | Commit |
|---|---|---|
| `inn-help-line` | The Inn's room help lines cut off ("...for 10000G a") | 8072cad, 210f6be |
| `card-mode-labels` | Card battle mode labels ran together ("AUTOAUTOMANUMANU"); now AUT and MAN | 7199a30 |
| `card-levelup-arrow` | Card level-up screen showed "1 A 2" for "1 → 2" | ab1771f |
| `status-help-line` | Status screen help line cut off | 1bc0171, 6764806 |
| `settings-name-layout` | Settings names placed for Japanese; "Sound" became "Music" | 6e8f023, e1661ce |
| `change-name-keyboard` | Change Name opened the keyboard on hiragana | 9e6d80c |
| `name-dragonaire` | Built-in name "Dragonare"; now Dragonaire, as in Wizardry V | ba9b96d |
| `name-old-drummer` | Built-in name "Old Drumer"; now Old Drummer | ba9b96d |
| `name-displacer-robe` | Built-in name "DISPLASER ROBE"; now DISPLACER ROBE | ba9b96d |
| `mythical-names` | Compendium's Mythical list: Shocitnal, Oserotoru, Inkuintori, Kuautori; now the Nahuatl names | 2dcc4fa |
| `bestiary-names` | Garbled names in the rest of the bestiary (Uthiu, Sopirote...); now as their sources spell them | 7940121 |
| `name-smelia` | スメリア was "Stink Man" in the Compendium, "Smelia" in battle; now Smelia in both | e053e3a |
| `name-breastplate` | Built-in name "B-PLATE OF GOODNESS"; now BREASTPLATE OF BOONS | 859fab6 |
| `name-iron-gloves` | Built-in name "STEEL GLOVES" for 鉄の小手; now IRON GLOVES, as in Wizardry III's ports | 6c01bd6 |
| `jpn-lock` | "Jpn" names drew as a jumble; the switches are now locked on "Eng" | 18ea18f |

No natural before/after pair exists for Boltac's Trade captions (f5d4e8f), the event
box glyph pool (6dc52dd), the voicing marks in event text (9a955ba), event line
centering (fc8eabc), catalog letter spacing (249f928), the descriptions under tall item
pictures (7e46b2f, 6d26caf), the training maze sign (ec26800), the stat-change
messages (001498f), the Small Shadow unidentified name (345f445), TABLET OF THE SUN
(8336160; no capture reaches the item), NPC speech closing its quotes (b440faa), or the
original game's bug fixes (29233ff, 54596b4, 34cd45c, 1976612, 5b565b9, fc6158f, 3e36a06,
a9ed605, e4c0da7, c717515; their tests set the case up with RAM writes, see
docs/re/bugs.md).
