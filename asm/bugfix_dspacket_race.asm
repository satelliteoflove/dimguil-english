; Game bug fix: a disc read can't stall forever.
;
; Every file load goes through the CD library's DsRead (0x80038300), which has DsPacket
; (0x80036888) put four commands in the library's command queue: Pause, Setmode (with its
; mode byte), Setloc (with the position) and ReadN. Each queue slot is written in this
; order: packet id, command, parameter bytes, parameter pointer, then the queue count.
; The library sends queued commands from interrupts: its VSync callback asks the drive
; for its status, and the drive's answer starts the next slot of the packet. If the VSync
; lands while DsPacket is filling the Setmode slot (after the id, before the parameter
; pointer, about 48 instructions) and the drive answers before the interrupt returns, the
; dispatcher sends Setmode with a null parameter. CD_cw refuses it ("no param", -2), the
; packet never moves on, DsReadSync reports the whole file still to come, and the game
; waits for it forever. Seen as the "You've met someone!" lock (docs/engine-notes.md, "CD
; reads: the DsPacket race").
;
; The fix writes each slot's id last, after the rest of the slot, so the dispatcher can't
; take a slot that isn't finished. Same instruction count: the old id store becomes a nop,
; and the queue-count update uses s0 as its base (free there: it held the slot's parameter
; address, already stored) instead of at, which frees a slot for the id store. Both copies
; of the fill loop are changed (DsRead uses the second). The dispatcher only takes a slot
; whose id is non-zero, and every path that frees a slot writes its id back to 0, so a
; slot being filled always reads as empty until this store.
;
; Original code (Sony's libds, byte-identical on the Japanese disc). It's rare, about one
; lock per few dozen hours in Beetle and less on hardware, but it costs everything since
; the last save. Chris decided on 2026-10-13 to fix it rather than list it as a known
; issue (docs/re/bugs.md 1.12, docs/re/decisions.md 24).
.psx
.open "dirty/dimguil/SLPS_026.91", 0x8000f800

; first copy of the slot loop
.org 0x80036a10
    nop                         ; was: sw s5, 0(s1) (the id, written first)
.org 0x80036a58
    lui     s0, 0x800a          ; was: lui v0, 0x800a
    lw      v0, -0x7910(s0)     ; the queue count, 0x800986f0
    addiu   s3, s3, 1
    sw      s5, 0(s1)           ; the id, now last: the slot is complete
    addiu   v0, v0, 1
    sw      v0, -0x7910(s0)     ; was: lui at, 0x800a / sw v0, -0x7910(at)

; second copy (DsRead's path)
.org 0x80036b08
    nop                         ; was: sw s5, 0(s1)
.org 0x80036b50
    lui     s0, 0x800a
    lw      v0, -0x7910(s0)
    addiu   s3, s3, 1
    sw      s5, 0(s1)
    addiu   v0, v0, 1
    sw      v0, -0x7910(s0)

.close
