; Lock the four language switches (Item, Monster and Spell Names, Status) on English.
;
; The English font replaced the kana, so "Jpn" drew the Japanese name lists as a jumble
; of kanji and Latin letters. The switches are bytes at 0x80096378..7b (0 = Japanese,
; 1 = English); english_defaults.asm makes 1 the default. This keeps them there:
;
;   - the settings screens (Edge of Town, the maze's camp, a card battle's SELECT
;     screen) no longer move them off "Eng"; "Jpn" stays on screen, dimmed
;   - loading a save sets them to English whatever the save says (a save from the
;     Japanese game, or one made before this patch, may say Japanese)
;   - MCARD's own reset, and the card game's unpacking of the settings it saved when a
;     card battle began, give English
.psx

; Edge of Town and the maze's camp: the toggle for rows 0-3 wrote 1 if the byte was 0,
; else 0. Both branches now write 1 (s1 = 1).
.macro lock_toggles, file, z0
.open file, 0x800a1000
.org z0
    sb      s1, 0x6378(v1)          ; was sb zero (Item Names)
.org z0 + 0x2c
    sb      s1, 1(v1)               ; Monster Names
.org z0 + 0x5c
    sb      s1, 2(v1)               ; Spell Names
.org z0 + 0x8c
    sb      s1, 3(v1)               ; Status
.close
.endmacro

lock_toggles "dirty/dimguil/HAZURE.BIN", 0x800ac5c8
lock_toggles "dirty/dimguil/MAZE.BIN", 0x800d9cd8

.open "dirty/dimguil/MCARD.BIN", 0x800a1000
; Loading a save copies its 12 settings bytes over 0x80096378 with lwl/lwr pairs; the
; first word is the four switches. Both load paths store 0x01010101 there instead.
.org 0x800aae88                     ; was lwl/lwr t3, 0x1eb5(s5)
    lui     t3, 0x0101
    ori     t3, t3, 0x0101
.org 0x800acbb4                     ; was lwl/lwr t5, 0x1eb5(t2)
    lui     t5, 0x0101
    ori     t5, t5, 0x0101
; A settings reset (v0 = 0x80090000) zeroed the four switches, then set v1 = 1 for the
; rest (was: sb zero,0x6378(v0) / addiu v0,v0,0x6378 / addiu v1,zero,1 / sb zero,1..3(v0))
.org 0x800ad250
    addiu   v0, v0, 0x6378
    addiu   v1, zero, 1
    sb      v1, 0(v0)
    sb      v1, 1(v0)
    sb      v1, 2(v0)
    sb      v1, 3(v0)
.close

.open "dirty/dimguil/CMAIN.BIN", 0x800a1000
; A card battle packs the settings into the bits of 0x8008a260 when it starts and
; unpacks them when it ends. The unpacking loop reloaded the packed byte each time
; round; it's loaded once now, which leaves room to set bits 0-3 (was: lui v0 / addiu
; a0,v0,0x6378 / move v1,zero / lui a1, then the loop with lbu v0,-0x5da0(a1) / nop).
.org 0x800aa88c
    lui     a1, 0x8009
    lbu     t0, -0x5da0(a1)
    addiu   a0, a1, 0x6378
    move    v1, zero
@@unpack:
    ori     v0, t0, 0x0f            ; the four switches: English
    srav    v0, v0, v1
    addiu   v1, v1, 1
    andi    v0, v0, 1
    sb      v0, (a0)
    slti    v0, v1, 8
    bnez    v0, @@unpack
    addiu   a0, a0, 1
    nop
.if org() != 0x800aa8c0
    .error "english_only: the unpacking rewrite must end where the original loop did"
.endif

; The card battle's settings screen (SELECT) moves a byte with the spinner at
; 0x800adafc, given (min, max, step down, step up) on the stack: 0, 1, -1, 1. The four
; switches get a minimum of 1, so left does nothing there. Rows 0-4 step down on left,
; 5-7 on right, as before (the original's two calls are one now).
.org 0x800aa94c
    addiu   v0, zero, 1
    sh      v0, 0x12(sp)            ; max
    sh      v0, 0x16(sp)            ; step up
    addiu   v1, zero, -1
    sh      v1, 0x14(sp)            ; step down
    sltiu   v1, a0, 4
    sh      v1, 0x10(sp)            ; min: 1 for the four switches, else 0
    ori     a2, zero, 0x8000        ; left steps down
    addiu   a3, zero, 0x2000        ; right steps up
    sltiu   v0, a0, 5
    bnez    v0, @@call
    move    a0, a1                  ; the setting's byte
    addiu   a2, zero, 0x2000        ; ON/OFF rows: the other way round
    ori     a3, zero, 0x8000
@@call:
    jal     0x800adafc
    addiu   a1, sp, 0x10
    nop
    nop
    nop
.if org() != 0x800aa998
    .error "english_only: the settings-screen rewrite must end where the original did"
.endif
.close
