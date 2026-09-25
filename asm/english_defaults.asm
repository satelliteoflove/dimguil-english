; Default the four Configuration language switches (Items, Monsters, Spells, Menus)
; to English. They live at 0x80096378..7b (0 = Japanese, 1 = English) and are zeroed
; in two places: system init and New Game. With Menus = English the game draws the
; status screens with its own built-in English labels.
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800

; system init (was: sb zero,0x6378(v0) / addiu v0,v0,0x6378 / addiu v1,zero,1 / sb zero,1..3(v0))
.org 0x80012c88
    addiu   v0, v0, 0x6378
    addiu   v1, zero, 1
    sb      v1, 0(v0)
    sb      v1, 1(v0)
    sb      v1, 2(v0)
    sb      v1, 3(v0)

; New Game (v0 = 1, a1 = 0x80096378 here; was sb zero,...)
.org 0x80023f68
    sb      v0, 0(a1)
    sb      v0, 1(a1)
    sb      v0, 2(a1)
    sb      v0, 3(a1)

.close
