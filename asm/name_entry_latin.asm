; Open name entry on the Latin letter grid instead of hiragana.
;
; 0x80079990 holds the character set (0 hiragana, 1 katakana, 2 Latin).
; 0x80079965 is a small state machine polled every frame:
;   0 = first-time setup (panels, labels), then 1
;   1/2/3 = draw the grid for set 0/1/2, then 4
;   4 = input. SELECT bumps the set (wrapping at 3) and writes set+1 here.
; State 1 hardcoded set 0, so the first grid was always hiragana. Here the open code
; sets the charset to Latin and state 1 draws whatever the charset byte says, so
; SELECT's wrap back to hiragana still works. The cancel reset (JOUKA 0x800b8948,
; HAZURE 0x800aef00) is left alone.
.psx

; Training Hall (create / rename)
.open "dirty/dimguil/JOUKA.BIN", 0x800a1000
.org 0x800af8b0             ; was: lui v0,0x8008 / sb zero,-0x6670(v0)  (v0 already 0x80080000)
    addiu   v1, zero, 2     ; v1 is reloaded at 0x800af8bc
    sb      v1, -0x6670(v0)
.org 0x800b8558             ; state 1 (delay slot), was: move a0,zero; s1 = 0x80080000
    lbu     a0, -0x6670(s1)
.close

; City Outskirts, Tome of Rebirth
.open "dirty/dimguil/HAZURE.BIN", 0x800a1000
.org 0x800ace48             ; was: sb zero,-0x6670(v0) / lui v0,0x8008  (redundant reload)
    addiu   v1, zero, 2     ; v1 is reloaded at 0x800ace50
    sb      v1, -0x6670(v0)
.org 0x800aeab8             ; state 1 (delay slot), was: move a0,zero; s0 = 0x80080000
    lbu     a0, -0x6670(s0)
.close
