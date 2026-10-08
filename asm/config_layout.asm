; Configuration screen: line the setting names up on the left.
;
; The screen's layout is a table of (x, y, string) halfwords, one entry per line, the
; title first and "Done" last. The names' x values right-align the Japanese at x = 160
; (160 - 12 * length), which left the English names ragged on both sides and ran "Spell
; Names" into its "(". Here every name starts at x = 80; the widest, "Monster Names", ends
; at 156, and the names with their options (to x = 256) sit centred on the screen. The
; title (centred by the printer) and "Done" keep their places.
;
; The table is in the Edge of Town overlay (HAZURE.BIN) and again in the maze (MAZE.BIN).
.psx

.macro config_names, file, addr
.open file, 0x800a1000
.org addr + 6               ; after the title; was x = 76, 64, 100, 100, 76, 76, 88, 64
    .dh 80, 56, 62          ; Item Names
    .dh 80, 68, 63          ; Monster Names
    .dh 80, 80, 64          ; Spell Names
    .dh 80, 92, 65          ; Status
    .dh 80, 104, 66         ; Sound Output
    .dh 80, 116, 67         ; Music
    .dh 80, 128, 68         ; Sound Effects
    .dh 80, 140, 69         ; Effects
.close
.endmacro

config_names "dirty/dimguil/HAZURE.BIN", 0x800a10a8
config_names "dirty/dimguil/MAZE.BIN", 0x800a1cbc
