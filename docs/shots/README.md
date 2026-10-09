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
| `inn-help-line` | The Inn's room help lines cut off ("...for 10000G a") | 8072cad, 2a207be |
| `card-levelup-arrow` | Card level-up screen showed "1 A 2" for "1 → 2" | ab1771f |
| `status-help-line` | Status screen help line cut off | 1bc0171, 6764806 |
| `settings-name-layout` | Settings names placed for Japanese; "Sound" became "Music" | 6e8f023, e1661ce |
| `change-name-keyboard` | Change Name opened the keyboard on hiragana | 9e6d80c |
| `jpn-lock` | "Jpn" names drew as a jumble; the switches are now locked on "Eng" | 18ea18f |

No natural before/after pair exists for Boltac's Trade captions (f5d4e8f), the event
box glyph pool (6dc52dd), the voicing marks in event text (9a955ba), event line
centering (fc8eabc), catalog letter spacing (249f928), the descriptions under tall item
pictures (7e46b2f, 6d26caf), the training maze sign (ec26800) or the stat-change
messages (001498f).
