.psx

EXTRA_SPACING equ 1
DEFAULT_SPACING equ 0xc
CHARSET_SIZE equ 0xd1

CENTERING_OFFSET equ 0x9
BATTLE_CENTERING_SPACING equ 0x6

.open "clean/dimguil/SLPS_026.91", "dirty/dimguil/SLPS_026.91", 0x8000f800
    // Fix text centering (one of many)
    // [Center-aligned descriptions] [1/2] Affects first line of dialogue only
    .org 0x8001fc18
    centering_desc_wrapper_2a_end:
    .org 0x8001fc1c
    centering_desc_wrapper_2b_end:
    .org 0x8001fc80
        j       centering_desc_wrapper_2a
        nop
    .org 0x8001fca4
        j       centering_desc_wrapper_2b
        nop
    .org 0x8001fcac
        sra     v0, a2, 0x1         // Never executed?
        lui     v1, 0x8008
        addiu   v1, v1, -0x6528
        addu    v1, s0, v1
        sra     v0, a2, 0x1         // Workaround for the above
        lb      v1, 0x0(v1)
        addi    v0, v0, CENTERING_OFFSET
        beq     v1, zero, @@LAB_8001fcdc
        sra     a0, v0, 0x18
        nop
        j       @@LAB_8001fce0
        sll     a0, v0, 1
        @@LAB_8001fcdc:
        move    a0, v0
        @@LAB_8001fce0:

    .org 0x80020170
    centering_desc_wrapper_1a_end:
    .org 0x80020174
    centering_desc_wrapper_1b_end:
    .org 0x800201d8
        j       centering_desc_wrapper_1a
        nop
    .org 0x800201fc
        j       centering_desc_wrapper_1b
        nop
    // [2/2] Affects subsequent lines
    .org 0x80020204
        // Same workaround as [1/2]
        sra     v0, a3, 0x1
        lui     v1, 0x8008
        addiu   v1, v1, -0x6528
        addu    v1, s3, v1
        sra     v0, a3, 0x1
        lb      v1, 0(v1)
        addi    v0, v0, CENTERING_OFFSET
        beq     v1, zero, @@LAB_80020234
        sra     a0, v0, 0x18
        nop
        j       @@LAB_80020238
        sll     s0, v0, 1
        @@LAB_80020234:
        move    s0, v0
        @@LAB_80020238:

    // VWF (center-aligned descriptions)
    .org 0x80020274
        j       VWF_desc_wrapper

    .org 0x8002027c
    VWF_desc_wrapper_end:
        ;lhu     v0,0x12(sp)

    // Make large text variable-width
    .org 0x8001f9d8
        lui     v1,0x8008
        lhu     v1,-0x6782(v1)
        nop
        andi    v0,v1,0x1
        beq     v0,zero,@@LAB_8001fa60
        move    t0,a2
        lui     v1,0x8008
        lbu     v1,-0x68fb(v1)
        nop
        andi    v0,v1,0x1
        beq     v0,zero,@@LAB_8001fa14
        nop
        lhu     v0,0x0(a1)
        j       @@LAB_8001fa38
        addiu   v0,v0,0xc
        ;j       set_VWF_spacing_a1
        ;nop

        @@LAB_8001fa14:
        andi    v0,v1,0x2
        beq     v0,zero,@@LAB_8001fa2c
        nop
        lhu     v0,0x0(a1)
        j       @@LAB_8001fa38
        addiu   v0,v0,0x6

        @@LAB_8001fa2c:
        lhu     v0,0x0(a1)
        nop
        addiu   v0,v0,0x8

        @@LAB_8001fa38:
        sh      v0,0x0(a1)
        sh      t0,0x0(a0)
        lui     v0,0x8008
        lhu     v0,-0x6782(v0)
        nop
        andi    v0,v0,0xfffe
        lui     at,0x8008
        sh      v0,-0x6782(at)

        @@LAB_8001fa58:
        jr      ra
        nop

        @@LAB_8001fa60:
        andi    v0,v1,0x2
        beq     v0,zero,@@LAB_8001fa90
        andi    v0,v1,0x8000
        sh      a2,0x0(a0)
        lui     v0,0x8008
        lhu     v0,-0x6782(v0)
        nop
        andi    v0,v0,0xfffd
        lui     at,0x8008
        sh      v0,-0x6782(at)
        jr      ra
        nop

        @@LAB_8001fa90: 
        bne     v0,zero,@@LAB_8001fa58
        andi    a3,a3,0xff
        li      v0,0xff
        beq     a3,v0,LAB_8001fb44
        nop
        lui     v1,0x8008
        lbu     v1,-0x68fb(v1)
        nop
        andi    v0,v1,0x1
        beq     v0,zero,LAB_8001fad0
        andi    v0,v1,0x2
        lhu     v0,0x0(a0)
        nop
        j       VWF_inject_1
        nop
        ;addiu   v0,v0,0xc
        ;jr      ra
        ;sh      v0,0x0(a0)
        
        LAB_8001fad0:
        beq     v0,zero,@@LAB_8001faec
        andi    v0,v1,0x4
        lhu     v0,0x0(a0)
        nop
        addiu   v0,v0,0x6
        jr      ra
        sh      v0,0x0(a0)

        @@LAB_8001faec:
        beq     v0,zero,@@LAB_8001fb08
        andi    v0,v1,0x8
        lhu     v0,0x0(a0)
        nop
        addiu   v0,v0,-0x8
        jr      ra
        sh      v0,0x0(a0)
        
        @@LAB_8001fb08:
        beq     v0,zero,@@LAB_8001fb34
        lui     v0,0x8006
        addiu   v0,v0,-0x18dc
        addu    v0,a3,v0
        lbu     v0,0x0(v0)
        lhu     v1,0x0(a0)
        sll     v0,v0,0x18
        sra     v0,v0,0x18
        addu    v1,v1,v0
        jr      ra
        sh      v1,0x0(a0)

        @@LAB_8001fb34:
        lhu     v0, 0x0(a0)
        nop
        ;j       set_VWF_spacing_a0
        addiu   v0,v0,0x8

        sh      v0, 0x0(a0)
        LAB_8001fb44:
        jr      ra
        nop

    // Used by BATTLE.BIN
    // Centering
    org 0x80022048
        centering_BATTLE_wrapper_1a_end:
    org 0x8002204c
        centering_BATTLE_wrapper_1b_end:
    org 0x800220b4
        j       centering_BATTLE_wrapper_1a
        nop
    org 0x800220d8
        j       centering_BATTLE_wrapper_1b
        nop

    .org  80060e97h
    .area 80060fe7h-.
    VWF_LUT:
        //  0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -, A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V, W, X, Y, Z, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, :
        .db 6, 3, 5, 5, 5, 5, 5, 5, 5, 5, 4, 7, 6, 6, 6, 6, 6, 6, 7, 3, 5, 7, 6, 9, 7, 6, 6, 6, 6, 6, 7, 7, 6, 9, 7, 6, 6, 4, 5, 4, 4, 4, 4, 5, 6, 3, 4, 5, 3, 7, 5, 4, 5, 5, 4, 4, 4, 5, 5, 7, 5, 5, 4, 3
        //  th, he, in, en, nt, re, er, an, ti, es, on, nd, ed, ou, to, ha, ea, st, at, hi, it, ve, as, or, ar, te, ng, is, le  al, se, ne, et, de, sa, si, ra, ld, ur, of, ll, yo, Yo, ro, oo, el, ch, ss, no, ck, be, ty, ca, ee, ri, lo, ir, ai, fo, ce, co, ac, ho, ge, pe, gh, la, li, un, sh, ot, ad, wi, do, up, ,+\w, e+\w, s+\w, d+\w, t+\w, n+\w  r+\w, y+\w
        .db 11, 11,  9, 10, 10,  9, 9,  10,  8,  9, 10, 10,  9, 10,  9, 11,  9,  9,  9, 10,  8, 10,  9,  9,  9,  9, 11,  8,  8,  8,  9, 10,  9,  9,  9,  8,  9,  8, 10,  9,  7, 10, 11,  9,  9,  8, 11,  9, 10, 10, 10, 10,  9,  9,  8,  8,  8,  8,  9,  9,  9,  9, 11, 10, 10, 12,  8,  7, 11, 11,  9,  9, 11,  9, 11,    6,    8,    8,    8,    8,    9,    8,    9
        // Ancient symbols
        //   A,  B,  C,  D,  E,  F,  G,  H,  I,  J,  K,  L,  M,  N,  O,  P,  Q,  R,  S,  T,  U,  V,  W,  X,  Y,  Z
        .db 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11
        //  g+\w, .+\w, (, ), +, A+\w, UP, DOWN, of, "", w+\w, tab_4, tab_8,  , !,  #, ol, ta, di, 's, ?, .,  ~, ', *, //, ,, [, ..., ],  Th,  ;, gl,  %,  &, ph,  /
        .db    9,    5, 3, 3, 5,   11,  7,    7, 15,  3,   11,    15,    31, 3, 3, 11,  8,  9,  8,  7, 5, 1, 11, 2, 5, 11, 2, 3,   5, 3,  12,  2,  9, 11, 11, 12,  5
        //  ma, me, wa, we, mo, mi
        .db 12, 12, 12, 12, 12, 11
        .align

    centering_HAZURE_wrapper:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_overlay_wrapper
        nop
        lw      ra, 0(sp)
        j       LAB_HAZURE_800bca78
        addiu   sp, sp, 4

    centering_JOUKA_wrapper:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_overlay_wrapper
        nop
        lw      ra, 0(sp)
        j       LAB_JOUKA_800dbe58
        addiu   sp, sp, 4
    
    centering_MAZE_wrapper:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_overlay_wrapper
        nop
        lw      ra, 0(sp)
        j       LAB_MAZE_800a1fa8
        addiu   sp, sp, 4

    centering_MCARD_wrapper:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_overlay_wrapper
        nop
        lw      ra, 0(sp)
        j       LAB_MCARD_800ad644
        addiu   sp, sp, 4

    .endarea

    .org  80073a40h
    .area 80073c74h-.
    VWF_desc_wrapper:
        addi    sp, sp, -4
        sw		s0, 0(sp)
        jal     0x8001f9d8
        move    s0, s2
        lw      s0, 0(sp)
        nop
        j       VWF_desc_wrapper_end
        addiu   sp, sp, 4

    .func centering_desc_wrapper_1_common
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     save_registers
        nop
        jal     get_VWF_spacing_in_a0
        // Current char is in a0
        move    s0, a0
        // Cumulative spacing in a3
        jal     restore_registers
        addu    a3, a0
        lw      ra, 0(sp)
        nop
        jr      ra
        addiu   sp, sp, 4
    .endfunc

    centering_desc_wrapper_1a:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_desc_wrapper_1_common
        nop
        lw      ra, 0(sp)
        j       centering_desc_wrapper_1a_end
        addiu   sp, sp, 4

    centering_desc_wrapper_1b:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_desc_wrapper_1_common
        nop
        lw      ra, 0(sp)
        j       centering_desc_wrapper_1b_end
        addiu   sp, sp, 4

    .func centering_desc_wrapper_2_common
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     save_registers
        nop
        jal     get_VWF_spacing_in_a0
        // Current char is in v1
        move    s0, v1
        // Cumulative spacing in a2
        jal     restore_registers
        addu    a2, a0
        lw      ra, 0(sp)
        nop
        jr      ra
        addiu   sp, sp, 4
    .endfunc

    centering_desc_wrapper_2a:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_desc_wrapper_2_common
        nop
        lw      ra, 0(sp)
        j       centering_desc_wrapper_2a_end
        addiu   sp, sp, 4

    centering_desc_wrapper_2b:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_desc_wrapper_2_common
        nop
        lw      ra, 0(sp)
        j       centering_desc_wrapper_2b_end
        addiu   sp, sp, 4

    VWF_inject_1:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     save_registers
        nop
        jal     get_VWF_spacing_in_a0
        // Current char in s0, no need to copy
        nop
        // Cumulative spacing in v0
        jal     restore_registers
        addu    v0, a0
        lw      ra, 0(sp)
        addiu   sp, sp, 4
        jr      ra
        sh      v0,0x0(a0)

    .func centering_BATTLE_wrapper_common
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     save_registers
        nop
        jal     get_VWF_spacing_in_a0
        // Current char in a2 and v1
        move    s0, a2
        // Cumulative spacing in t9 instead of t0
        addu    t9, a0
        jal     restore_registers
        // Increment t0 (number of chars)
        addiu   t0, 1
        lw      ra, 0(sp)
        nop
        jr      ra
        addiu   sp, sp, 4
    .endfunc
    
    centering_BATTLE_wrapper_1a:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_BATTLE_wrapper_common
        nop
        lw      ra, 0(sp)
        j       centering_BATTLE_wrapper_1a_end
        addiu   sp, sp, 4

    centering_BATTLE_wrapper_1b:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     centering_BATTLE_wrapper_common
        nop
        lw      ra, 0(sp)
        j       centering_BATTLE_wrapper_1b_end
        addiu   sp, sp, 4

    centering_overlay_wrapper:
        addi    sp, sp, -4
        sw		ra, 0(sp)
        jal     save_registers
        nop
        jal     get_VWF_spacing_in_a0
        move    s0, v1
        jal     restore_registers
        addu    a1, a0
        lw      ra, 0(sp)
        nop
        jr      ra   
        addiu   sp, sp, 4

    // Generalized VWF
    .func save_registers
        addi    sp, sp, -20
        sw		s0, 16(sp)
        sw      t2, 12(sp)
        sw      t3, 8(sp)
        sw      t4, 4(sp)
        jr      ra
        sw      a0, 0(sp)
    .endfunc
    .func restore_registers
        lw      a0, 0(sp)
        lw      t4, 4(sp)
        lw      t3, 8(sp)
        lw      t2, 12(sp)
        lw      s0, 16(sp)
        jr      ra
        addiu   sp, sp, 20
    .endfunc
    .func get_VWF_spacing_in_a0
        la      t2, VWF_LUT
        lui     t4, CHARSET_SIZE
        ble     s0, t4, @@is_VWF
        nop
        jr	    ra
        ori     a0, zero, DEFAULT_SPACING
        @@is_VWF:
        addu    t2, t2, s0
        lb      t3, (t2)
        nop
        jr	    ra
        addiu   a0, t3, EXTRA_SPACING
    .endfunc

    .endarea
.close //SLPS_026.91

// Fix text centering across all overlays
.open "clean/dimguil/JOUKA.BIN", "dirty/dimguil/JOUKA.BIN", 0x800a1000
    .org 0x800dbe4c
        bne     v0, zero, LAB_JOUKA_800dbe58
        addiu   v0, a0, 1
        j       centering_JOUKA_wrapper 
        LAB_JOUKA_800dbe58:
    
    .org 0x800dbe70
        sra     v1, a1, 1        ;sll     v0, a1, 0x18
        nop                      ;sra     v0, v0, 0x18
        nop                      ;sll     v1, v0, 0x1
        nop                      ;addu    v1, v1, v0
        nop                      ;sll     v1, v1, 0x1
        li      v0, 0xa8
        subu    s1, v0, v1
.close  

.open "clean/dimguil/HAZURE.BIN", "dirty/dimguil/HAZURE.BIN", 0x800a1000
    .org 0x800bca6c
        bne     v0, zero, LAB_HAZURE_800bca78
        addiu   v0, a0, 1
        j       centering_HAZURE_wrapper 
        LAB_HAZURE_800bca78:
    
    .org 0x800bca90
        sra     v1, a1, 1        ;sll     v0, a1, 0x18
        nop                      ;sra     v0, v0, 0x18
        nop                      ;sll     v1, v0, 0x1
        nop                      ;addu    v1, v1, v0
        nop                      ;sll     v1, v1, 0x1
        li      v0, 0xa8
        subu    s1, v0, v1
.close  

.open "clean/dimguil/MCARD.BIN", "dirty/dimguil/MCARD.BIN", 0x800a1000
    .org 0x800ad638
        bne     v0, zero, LAB_MCARD_800ad644
        addiu   v0, a0, 1
        j       centering_MCARD_wrapper 
        LAB_MCARD_800ad644:
    
    .org 0x800ad65c
        sra     v1, a1, 1        ;sll     v0, a1, 0x18
        nop                      ;sra     v0, v0, 0x18
        nop                      ;sll     v1, v0, 0x1
        nop                      ;addu    v1, v1, v0
        nop                      ;sll     v1, v1, 0x1
        li      v0, 0xa8
        subu    s1, v0, v1
.close  

.open "clean/dimguil/MAZE.BIN", "dirty/dimguil/MAZE.BIN", 0x800a1000
    .org 0x800a1f9c
        bne     v0, zero, LAB_MAZE_800a1fa8
        addiu   v0, a0, 1
        j       centering_MAZE_wrapper 
        LAB_MAZE_800a1fa8:
    
    .org 0x800a1fc0
        sra     v1, a1, 1        ;sll     v0, a1, 0x18
        nop                      ;sra     v0, v0, 0x18
        nop                      ;sll     v1, v0, 0x1
        nop                      ;addu    v1, v1, v0
        nop                      ;sll     v1, v1, 0x1
        li      v0, 0xa8
        subu    s1, v0, v1
.close

.open "clean/dimguil/BATTLE.BIN", "dirty/dimguil/BATTLE.BIN", 0x800a1000
    .org 0x800d2038
        li      t0, 1

    .org 0x800d2150
        li      t0, 0xc
        li      t9, 0
    
    .org 0x800d21d0
        nop
        move    t0, t9
    .org 0x800d21ec
        li      t9, 0

    .org 0x800d3120
        move    v1, v0
        ;sra     v1, v0, 0x1
.close

