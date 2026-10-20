; Translation: the naughty-name list (MCARD 0x800a1eb0, lengths at 0x800a1f28).
;
; The original has a naughty-name filter. When a party member's name is one of twelve
; rude words, the greeting turns to a line where the character is too embarrassed to say
; it: Lychee's 1:72 in Guy's party (picker 0x800be88c) and, since
; bugfix_rosea_greeting.asm, Rosea's 2:56 in Balbo's. Their embarrassment is the joke.
; (Guy's picker loads the list's bytes signed, so the 0xff terminator never matches and
; Lychee's line can't show with any list; docs/re/bugs.md 2.9. Rosea's check compares
; unsigned.) The Japanese list is six words, each as hiragana then katakana; a name typed on
; the patch's Latin grid can never match it, so this is the list in English, each word
; in its Japanese word's slot, ALL CAPS then Capitalized. Chris chose the words
; (2026-10-19):
;
;   0-1   DICK / Dick       was ちんこ / チンコ
;   2-3   COCK / Cock       was ちんぽ / チンポ
;   4-5   CUNT / Cunt       was まんこ / マンコ
;   6-7   SHIT / Shit       was かたておち / カタテオチ (Chris chose a crude name over an
;                           equivalent for this slot)
;   8-9   RETARD / Retard   was きちがい / キチガイ
;   10-11 BALLS / Balls     was きんたま / キンタマ
;
; Each entry is the bytes a name typed on the Latin grid (MAIN 0x8005e120 + 132) is stored
; as: one code per letter (A-Z 0x0b-0x24, a-z 0x25-0x3e), then 0xff and 0x40, padded to
; 10 bytes. The match is on the whole name, terminator included, so "Dickens" or "dick"
; doesn't match; each length counts the 0xff and 0x40.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000

.org 0x800a1eb0
.area 0x800a1f28 - .
    .byte 0x0e,0x13,0x0d,0x15,0xff,0x40,0,0,0,0     ; DICK
    .byte 0x0e,0x2d,0x27,0x2f,0xff,0x40,0,0,0,0     ; Dick
    .byte 0x0d,0x19,0x0d,0x15,0xff,0x40,0,0,0,0     ; COCK
    .byte 0x0d,0x33,0x27,0x2f,0xff,0x40,0,0,0,0     ; Cock
    .byte 0x0d,0x1f,0x18,0x1e,0xff,0x40,0,0,0,0     ; CUNT
    .byte 0x0d,0x39,0x32,0x38,0xff,0x40,0,0,0,0     ; Cunt
    .byte 0x1d,0x12,0x13,0x1e,0xff,0x40,0,0,0,0     ; SHIT
    .byte 0x1d,0x2c,0x2d,0x38,0xff,0x40,0,0,0,0     ; Shit
    .byte 0x1c,0x0f,0x1e,0x0b,0x1c,0x0e,0xff,0x40,0,0   ; RETARD
    .byte 0x1c,0x29,0x38,0x25,0x36,0x28,0xff,0x40,0,0   ; Retard
    .byte 0x0c,0x0b,0x16,0x16,0x1d,0xff,0x40,0,0,0  ; BALLS
    .byte 0x0c,0x25,0x30,0x30,0x37,0xff,0x40,0,0,0  ; Balls
.endarea

.org 0x800a1f28                 ; compare lengths, bytes, terminator included
    .byte 6,6, 6,6, 6,6, 6,6, 8,8, 7,7

.close
