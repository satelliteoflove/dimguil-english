; Game bug fix: special chat topics with low block numbers can play.
;
; Guy's, Balbo's and Fontana's Talk first stored a random topic in talk_block, then
; replaced it with a special topic when the location, stage or a story flag called for
; one, then kept talk_block 90% of the time if it was above the random range (> 11, or
; > 7 for Fontana), and otherwise rolled a fresh topic. Specials numbered inside the
; range were always thrown away:
;   Guy 9-11, the topics for areas 1-4 and 0x17-0x1b (NPC_MES1 195-210)
;   Balbo 6-8, "about other parties", by stage (NPC_MES2 174-187)
;   Fontana 6 and 7, two of the stage-1 specials (NPC_MES3 181-196)
; The first random topic was never used: anything not special is rolled again. So it
; becomes -1, meaning "no special", and the test becomes "kept if 0 or more".
; docs/re/bugs.md 1.8.
.psx
.open "dirty/dimguil/MCARD.BIN", 0x800a1000
; Guy (talk_guy)
.org 0x800b670c
    sh      s1, -0x67e4(v0)     ; talk_state = 0x28 (was the delay slot of jal rand_upto(11))
    addiu   v0, zero, -1        ; no special yet; stored to talk_block at 0x800b6720
.org 0x800b6b28
    slti    v0, v0, 0           ; was 0xc
; Balbo (talk_balbo)
.org 0x800c951c
    sh      v0, -0x67e4(v1)     ; talk_state = 0x28
    addiu   v0, zero, -1        ; stored to talk_block at 0x800c9530
.org 0x800c9a28
    slti    v0, v0, 0           ; was 0xc
; Fontana (talk_fontana)
.org 0x800d12b0
    sh      v0, -0x67e4(v1)     ; talk_state = 0x28
    addiu   v0, zero, -1        ; stored to talk_block at 0x800d12d0
.org 0x800d1394
    slti    v0, v0, 0           ; was 8
.close
