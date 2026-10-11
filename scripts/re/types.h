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

/* Roster record, 0xd0 bytes, 20 of them at 0x8007d708 in the Training Hall's roster order.
 * Field notes: docs/re/G-records.md. "code" = code read, "RAM" = checked in a RAM dump. */
typedef struct Roster {
    u8  name[10];        /* +0x00 game encoding, ff40-terminated, 8 glyphs at most (code: copied
                            as 10 bytes everywhere; the clear routine writes ff40 + 8 zeros) */
    u8  race_align;      /* +0x0a bits 0-5 race 0-10 (Human Elf Dwarf Gnome Hobbit Faerie
                            Lizardman Dracon Rawulf Mook Felpurr), bits 6-7 alignment 0 Good,
                            1 Neutral, 2 Evil (confirmed: status screen labels, class tables) */
    u8  class_sex;       /* +0x0b bits 0-6 class 0-13 (Fighter Mage Priest Thief Samurai Lord
                            Valkyrie Ranger Bard Alchemist Psionic Bishop Ninja Monk), bit 7
                            female (confirmed: status labels; Valkyrie needs bit 7) */
    u8  portrait;        /* +0x0c 0 = the class's portrait, else a special one (inferred:
                            0x800e6598 picks class or portrait+0x14) */
    u8  unk0d;           /* +0x0d no reader found */
    u16 status;          /* +0x0e bits: 1 afraid, 2 confused, 4 poisoned, 8 asleep, 0x10 K.O.,
                            0x20 paralyzed, 0x40 stoned, 0x80 dead, 0x100 ashes, 0x200 lost;
                            the highest set bit is the one shown (confirmed: 0x800d8804).
                            >= 0x20 counts as out of action (rescue offer, inn, etc.) */
    u8  age_years;       /* +0x10 (confirmed: status screen, class change +3) */
    u8  age_weeks;       /* +0x11 0-51, carries into years at 52 (confirmed: code) */
    u8  age_days;        /* +0x12 0-6, carries into weeks at 7 (confirmed: inn code) */
    s8  stats[6];        /* +0x13 Str, IQ, Pie, Vit, Agi, Luc (confirmed: status screen) */
    u8  unk19[3];        /* +0x19 no reader found (padding) */
    u32 gold;            /* +0x1c (confirmed) */
    u16 items[10];       /* +0x20 low 9 bits item id; 0x0800 sub-hand weapon, 0x1000 main
                            hand, 0x2000 equipped, 0x4000 identified, 0x8000 cursed (stuck
                            when equipped); 0xffff empty (confirmed: equip code 0x800cffcc,
                            shop, identify) */
    u8  item_state[10];  /* +0x34 per slot: uses left for potions and scrolls (subtypes 0x14,
                            0x15; Boltac sells them with 5); 0xfb-0xfe shown as special marks
                            in Boltac's inspect (confirmed: code) */
    u8  unk3e[2];        /* +0x3e no reader found */
    u32 exp;             /* +0x40 (confirmed: EXP table check, RAM) */
    u16 level;           /* +0x44 (confirmed) */
    s16 hp;              /* +0x46 (confirmed) */
    u16 max_level;       /* +0x48 highest level reached (inferred: raised with level, kept
                            through drains) */
    s16 max_hp;          /* +0x4a (confirmed) */
    u8  spells_known[4][4]; /* +0x4c per school (Mage, Priest, Alchemist, Psionic), one
                            nibble per spell level 1-7 (low nibble first), bits 1/2/4 = the
                            level's three spells (confirmed: 0x800b9090, 0x800b9540) */
    u8  spell_points[4][7]; /* +0x5c per school and spell level, 0-9 (confirmed: casting
                            decrements, recalc caps at 9) */
    u8  poison;          /* +0x78 HP lost per poisoned step (confirmed: 0x800c5570) */
    u8  unk79;           /* +0x79 a battle counter: set to 0x7f by hit effects, cut by 10 a
                            round, cleared on death (inferred) */
    u8  area;            /* +0x7a where the character is: 0xff in town, else the area it was
                            left in (confirmed: RAM read and code read) */
    u8  x;               /* +0x7b (confirmed: code read) */
    u8  y;               /* +0x7c */
    u8  facing;          /* +0x7d */
    /* +0x7e-0xbf: values derived from class and gear, recomputed when the gear changes and
       read mostly by battle (D-battle.md, "Roster fields used in battle"). */
    u8  unk7e;           /* +0x7e */
    u8  saves[4];        /* +0x7f four saving throws, rolled as rand(20) < value (D: code) */
    u8  unk83;           /* +0x83 */
    u16 to_hit;          /* +0x84 to-hit bonus (D: code) */
    s8  ac;              /* +0x86 armor class (confirmed: status screen, 0x800dc810) */
    u8  magic_resist[4]; /* +0x87 percent, by school Mage/Priest/Alchemist/Psionic (D: code;
                            battle sets +0x87 to 100 in 0x800ad658) */
    s8  regen;           /* +0x8b HP gained (or, negative, lost) per step in the maze and per
                            round in battle; items with a positive Item.regen add to it while
                            carried, negative ones while equipped (confirmed: 0x800c5570,
                            the shop and equip code; D) */
    u8  hit_effects;     /* +0x8c status bits the weapons inflict (D: code) */
    u8  hit_effect_pct[7]; /* +0x8d chances of those effects, percent (D: code) */
    s8  swings[2];       /* +0x94 extra swings, first and second weapon (D: code) */
    u8  dice[2][3];      /* +0x96 damage dice of the two weapons: n, sides, bonus (D: code) */
    s8  reach[2];        /* +0x9c reach of the two weapons (D: weapon_reach) */
    u8  unk9e[2];        /* +0x9e */
    u32 protect_mask;    /* +0xa0 monster classes whose hits are halved (D: code); copied to
                            +0xa4 at battle start (0x800a5b0c) */
    u32 unka4;           /* +0xa4 battle copy of protect_mask (inferred) */
    u32 slay_mask;       /* +0xa8 monster classes that take double damage, tested against
                            Monster.flags (D: code) */
    u16 unkac;           /* +0xac copied to +0xae at battle start */
    u16 resist_bits;     /* +0xae element and status resist bits (D: code) */
    u8  effect_resist[7]; /* +0xb0 resistance to the seven hit effects, percent (D: code) */
    u8  unkb7[3];        /* +0xb7 */
    u8  drain_resist;    /* +0xba resistance to level drain, percent (D: code) */
    u8  unkbb[5];        /* +0xbb */
    u32 kills;           /* +0xc0 monsters killed (confirmed: status screen label
                            さっしょうすう) */
    u8  deaths;          /* +0xc4 times died (confirmed: status screen, +1 on death) */
    u8  char_flags;      /* +0xc5 bit 0 a mark on the status screen; bits 1-4 set by town and
                            maze events (inferred) */
    u8  met_bits[3];     /* +0xc6 one bit per NPC meeting (talk opcode 0; confirmed) */
    u8  talk_flags;      /* +0xc9 more per-character talk flags, set by MCARD handlers
                            (inferred) */
    u8  marks[2];        /* +0xca bit 7 of +0xca and bits 0-3 of +0xcb pick the emblems drawn
                            beside the name (confirmed: 0x800d9f00); +0xca bits 0-1 set in
                            talks */
    u8  unkcc[4];        /* +0xcc */
} Roster;

/* A party: 20 records of 0x36 bytes at 0x8008f8c8 (confirmed: code read). The party you
 * walk with is mirrored at 0x8007e810 (current_party_id, then current_party_count and
 * current_members). */
typedef struct PartyRec {
    s8  id;              /* +0x00 -1 = unused */
    u8  count;           /* +0x01 members */
    s8  members[6];      /* +0x02 roster indexes, -1 = empty */
    u8  unk08[6];        /* +0x08 per member (seen 00 01 02 03 ff ff after a wipe) */
    u8  member_state[6]; /* +0x0e per member; set to 0xff when a member leaves (code) */
    u8  unk14[0x22];     /* +0x14 */
} PartyRec;

/* Item record, 0x4c bytes; 382 of them (ids 0-381) in the executable at 0x80052bf2,
 * resident (confirmed: id at +0 counts 0..381, code indexes it by id * 0x4c).
 * Packed: the u32s sit at odd halfword offsets. */
#pragma pack(push, 1)
typedef struct Item {
    u16 id;              /* +0x00 equals the index (confirmed: table scan) */
    u8  category;        /* +0x02 0 weapon, 1 armor, 2 shield, 3 helm, 4 gauntlets, 5 boots,
                            6 instrument, 7 other (confirmed: equip passes, names) */
    u8  subtype;         /* +0x03 kind and picture: 0-8 weapon kinds, 9-13 armor kinds, 14
                            shield, 15-16 helm/hat, 17 gloves, 18 boots, 19 instrument, 20
                            potion, 21 scroll, 22 cloak, 23 ankh, 24 ring, 25 amulet, 26
                            special, 28 monster card (confirmed: names; potions and scrolls
                            keep uses in Roster.item_state) */
    u8  flags04;         /* +0x04 bit 0 Good, 1 Neutral, 2 Evil may use it (else it curses
                            when equipped), 3 male, 4 female may equip; weapons: 5 two-handed,
                            6 main hand, 7 sub hand (confirmed: Boltac's inspect labels) */
    u8  specials;        /* +0x05 bits 0-6 special powers (counted by 特 in the weapon
                            compare), bit 7 cursed (confirmed: 0x800cffcc) */
    u8  unk06[7];        /* +0x06 values 0/5/10/15 */
    u8  equip_effect;    /* +0x0d effect when equipped or used: 1-6 stat up, 7-12 stat down,
                            0xd age -1, 0xe age +1, 0xf cure, 0x10 cure party, 0x11 max HP
                            up, 0x12 down, 0x13 spell points 9, 0x14 spell points 0, 0x15
                            forget spells, 0x16 poison, 0x17 ashes, 0x18 death, 0x19
                            paralysis, 0x1a stone, 0x1e become a Bishop ... (code:
                            0x800ccc94; full list in G-records.md) */
    u16 break_chance;    /* +0x0e percent chance, each use, that it turns into break_into
                            (confirmed: 0x800d8b04, battle 0x800ac7c4) */
    u16 break_into;      /* +0x10 item id it becomes (0 = BROKEN ITEM, then removed) */
    u32 price;           /* +0x12 Boltac's price (confirmed: buying subtracts it) */
    u32 sell;            /* +0x16 what Boltac pays (confirmed: selling) */
    u8  stock;           /* +0x1a Boltac's starting stock: 0 none, 0xff unlimited (confirmed: stock reset) */
    u8  battle_spell;    /* +0x1b spell cast when used in battle, low 7 bits; 0xff none
                            (inferred: battle 0x800a29b4) */
    u16 class_mask;      /* +0x1c bit per class who may equip (confirmed) */
    u16 race_mask;       /* +0x1e bit per race who may equip (confirmed) */
    u8  unk20;           /* +0x20 */
    s8  regen;           /* +0x21 HP per step: positive while carried, negative while
                            equipped (confirmed: shop, trade and equip code) */
    u8  unk22[0x13];     /* +0x22 bit fields at +0x22-0x27; 5-50 values at +0x28-0x34 */
    s8  ac;              /* +0x35 AC bonus (confirmed: inspect shows it) */
    s8  to_hit;          /* +0x36 当 in the weapon compare (confirmed: 0x800c2b84) */
    u8  dice_n;          /* +0x37 damage dice count (confirmed: max = n*sides + bonus) */
    u8  dice_sides;      /* +0x38 */
    s8  dice_bonus;      /* +0x39 */
    s8  extra_swings;    /* +0x3a 回, extra attacks (confirmed: weapon compare) */
    u8  unk3b[3];        /* +0x3b */
    u32 slay_mask;       /* +0x3e 倍, monster families it's strong against (confirmed: the
                            compare counts its bits) */
    u8  unk42[8];        /* +0x42 values 5-30 at +0x42-0x45, 1/2/4 at +0x46 */
    u16 unk4a;           /* +0x4a */
} Item;

/* Monster record, 0xd0 bytes: the last 0xd0 bytes of each DATA02/M_DTnnn.BIN and of the
 * NPC party files NPTnn.BIN (one per member). In battle the record of group g is at
 * monster_records (0x8008a918) + g*0xd0, groups 1-4 copied byte for byte from the file
 * (confirmed: RAM dump against M_DT004). Most fields are from battle analyst D's code
 * reads (D-battle.md, "Monster record fields used in battle"). */
typedef struct Monster {
    u8  names[6][0x12];  /* +0x00 Japanese, Japanese unidentified, English, English
                            unidentified, English plural, English unidentified plural
                            (confirmed: nptnames.py, RAM) */
    u16 id;              /* +0x6c monster number (confirmed: table scan, 0-334) */
    u8  unk6e;           /* +0x6e (12, 13, 10 most common; inferred: picture) */
    u8  group_dice[3];   /* +0x6f group size: count, sides, bonus (D: code) */
    u16 max_hp;          /* +0x72 heals and regeneration stop here (D: code) */
    u16 level;           /* +0x74 (D: code) */
    u16 hp_sides;        /* +0x76 HP = level d sides + bonus (D: code) */
    u16 hp_bonus;        /* +0x78 (D: code) */
    s16 ac;              /* +0x7a (D: code) */
    u32 exp;             /* +0x7c experience per monster (D: code) */
    u8  drain;           /* +0x80 levels drained per hit (D: code) */
    u8  regen;           /* +0x81 HP regenerated per round (D: code) */
    u8  unk82[6];        /* +0x82 */
    u16 ai;              /* +0x88 AI type, row of the action table, 1-based (D: code) */
    u8  flee_chance;     /* +0x8a percent (D: act_monster_flee) */
    u8  help_chance;     /* +0x8b rolled on 0-89 (D: act_call_help) */
    s16 companion;       /* +0x8c companion monster id, -1 none (D: code) */
    u8  companion_pct;   /* +0x8e (D: code) */
    u8  spells[4][5];    /* +0x8f per school (Mage, Priest, Alchemist, Psionic) five entries,
                            0xff none; read by monster_pick_spell 0x800d0c6c and scaled by 7
                            in groups_reorder (inferred: spell levels) */
    u8  magic_resist[4]; /* +0xa3 percent by school; +0xa5 is also the breath resistance
                            (D: code) */
    u8  unka7;           /* +0xa7 */
    u32 flags;           /* +0xa8 0x80000 undead, 0x100000 summoned, 0x400000/0x1000000
                            death-immune, 0x1000000 decapitation-immune; low bits the monster
                            class matched by slaying and protection (D: code) */
    u8  attacks[3][10];  /* +0xac three attacks: +0 noun (u16), +2 verb, +3 swings, +4-+6
                            damage dice, +7 effect bits (0x80 reaches the back row), +8
                            effect chance (D: code) */
    u8  breath_msg;      /* +0xca breath message: FIGHTMSG index + 50 (D: code). +0xc9, the
                            last byte of attacks[2], is the breath type (D) */
    u8  unkcb;           /* +0xcb */
    u16 resist_bits;     /* +0xcc status and element resist bits (D: code) */
    u16 weak_bits;       /* +0xce weaknesses: double dice, lower saves (D: code) */
} Monster;
#pragma pack(pop)
