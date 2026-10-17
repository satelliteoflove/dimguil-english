; Tavern recruits (JOUKA.BIN): the four whose built-in names were kana get English names
; (Chris, 2026-10-17): recruit 1 コロヒチ KOROCHI, 15 メタルヘッド METALHED, 17 ユーリー
; YURI, 19 ジーラ JEERA. The other sixteen were already in capital romaji.
;
; tavern_recruit (0x800ab08c) reads the names from a table of 10-byte slots at 0x800a1178
; (recruit n at + 10n): up to 8 letters, 0xff, 0x40, zero padding (docs/re/E-town.md). A
; recruit whose name is already in the roster isn't offered, so this table and the name in
; each recruit's own record (DATA06/7nn.DAT +0x2af8, recruit n is 701 + n, patched in
; binary/7nn.DAT.names.json) have to match. This is asm rather than a binary/ patch
; because vwf.asm copies JOUKA from clean/ after the binary patches are applied.
.psx
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000

.org 0x800a1178 + 10 * 1
.area 10
    .db 0x15, 0x19, 0x1c, 0x19, 0x0d, 0x12, 0x13, 0xff, 0x40, 0x00     ; KOROCHI
.endarea
.org 0x800a1178 + 10 * 15
.area 10
    .db 0x17, 0x0f, 0x1e, 0x0b, 0x16, 0x12, 0x0f, 0x0e, 0xff, 0x40     ; METALHED
.endarea
.org 0x800a1178 + 10 * 17
.area 10
    .db 0x23, 0x1f, 0x1c, 0x13, 0xff, 0x40, 0x00, 0x00, 0x00, 0x00     ; YURI
.endarea
.org 0x800a1178 + 10 * 19
.area 10
    .db 0x14, 0x0f, 0x0f, 0x1c, 0x0b, 0xff, 0x40, 0x00, 0x00, 0x00     ; JEERA
.endarea

.close
