/* Record layouts for Dimguil's globals, applied by scripts/re/ghidra.py (ApplySymbols.java
 * parses this file into every program and types the globals whose `type` column in
 * scripts/re/symbols/*.csv names one of these). Ghidra's C parser reads it, so: plain C,
 * no #include, fixed-size padding arrays for unknown stretches, every offset checked
 * against the record size. Mark each field confirmed or inferred, as in the CSVs.
 * When a field is learned, split the unk array around it and keep the total size. */

typedef unsigned char u8;
typedef signed char s8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef int s32;

/* Roster record, 0xd0 bytes, at 0x8007d708 in the Training Hall's roster order.
 * docs/cheats.md, docs/engine-notes.md "Body recovery by NPC parties". */
typedef struct Roster {
    u8  name[0x0e];      /* +0x00 name, game encoding, ff40-terminated (inferred length) */
    u16 status;          /* +0x0e 0 healthy; 0x80 dead (temple_dead state); the NPC rescue
                            offer counts >= 0x20 as a body (confirmed: code read) */
    u8  unk10[0x0c];
    u32 gold;            /* +0x1c (confirmed) */
    u16 items[10];       /* +0x20 item id in the low 9 bits, 0x2000 unidentified, 0xffff
                            empty (confirmed) */
    u8  item_state[10];  /* +0x34 per slot; 0xff when a slot is emptied (inferred: equipped,
                            cursed or the like) */
    u8  unk3e[2];
    u32 exp;             /* +0x40 experience (inferred, cheats.md) */
    u16 level;           /* +0x44 (inferred) */
    u16 hp;              /* +0x46 (inferred) */
    u16 max_level;       /* +0x48 (inferred) */
    u16 max_hp;          /* +0x4a (inferred) */
    u8  unk4c[0x2e];
    u8  area;            /* +0x7a where the character is: 0xff in town, else the area it
                            was left in (confirmed: RAM read and code read) */
    u8  x;               /* +0x7b (confirmed: code read) */
    u8  y;               /* +0x7c */
    u8  facing;          /* +0x7d */
    u8  unk7e[0x48];
    u8  met_bits[3];     /* +0xc6 one bit per NPC meeting (talk opcode 0; confirmed) */
    u8  unkc9[7];
} Roster;

/* A party: 20 records of 0x36 bytes at 0x8008f8c8 (confirmed: code read). */
typedef struct PartyRec {
    s8  id;              /* +0x00 -1 = unused */
    u8  count;           /* +0x01 members */
    s8  members[6];      /* +0x02 roster indexes, -1 = empty */
    u8  unk08[0x2e];
} PartyRec;
