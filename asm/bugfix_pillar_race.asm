; Game bug fix: a pillar guardian's fight always starts.
;
; Touching one of the four Grounds pillars opens the event box ("The pillar begins to
; shake ... attacks."), locks walking input and starts a dust animation (0x800cc9fc,
; once per logic frame). When the dust ends it requests the guardian's fight
; (0x80079bf1 = 2). The box closes itself once its text has typed out, and maze_frame
; clears 0x80079bf1 on every box close (0x800a3234). If the dust ends first, the request
; is wiped, nothing clears the input lock, and only a reset gets out. The Japanese text
; always finished well ahead of the dust; the longer English text finishes about when it
; does, and about 3% of pillar events locked up (docs/engine-notes.md, "Pillar
; guardians: the box and the dust race").
;
; The dust step now counts an open box (0x80079838) as dust still alive, so the count
; holds at 1 until the box has closed and the request is set after the clear. Both
; instructions replace nops: the first fills the load delay before the count test, the
; second the branch delay slot (v0 is the live particle count, read only by the next
; branch; a0 isn't read again before the next call sets it).
.psx
.open "dirty/dimguil/MAZE.BIN", 0x800a1000

.org 0x800cca20
    lbu     a0, -0x67c8(s0)     ; was: nop. The box flag, 0x80079838 (s0 = 0x80080000)

.org 0x800cca28
    or      v0, v0, a0          ; was: nop. Busy = particles alive or the box open

.close
