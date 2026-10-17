; Where vwf.asm puts VWF_LUT (the glyph widths, 0xd8 bytes) and the four overlay centering
; wrappers after it, in MAIN. catalog_vwf.asm includes this for the table's address, and
; scripts/descfit.py and scripts/screentext.py read VWF_LUT_AT from here.
;
; 0x800159b8-0x80015bf3 held FUN_800159b8 and FUN_80015ad8, two sprite-setup routines
; nothing calls, jumps to, branches into or takes the address of, in MAIN or any overlay;
; no read, write or execution there in a watched run of every chapter (docs/engine-notes.md,
; "The VWF block and libds's play list"). Remisse's patch had the block at 0x80060e97,
; inside libds DsPlay's state, where the ending's CD audio call wrote over it.
;
; VWF_LUT_AT keeps the old address's alignment (3 mod 4), so the bytes past the table,
; which codes 0xd8-0xff read (vwf.asm, get_VWF_spacing_in_a0), stay what they were.
VWF_BLOCK     equ 0x800159b8
VWF_LUT_AT    equ 0x800159bb
VWF_BLOCK_END equ 0x80015bf4
