# Tall item pictures: in-game check

Boltac's catalog (checklist item Q7). The 55 items with tall pictures now start their
description 9 px higher, so 5 lines fit instead of 4. To make room, each tall picture
was cut from 152 to 143 rows: some only lost empty parchment, some had the item moved
up a few pixels, and some had the item shrunk. The item sits on the panel's own
parchment, so the texture should line up with the parchment around it.

**How to look:** start the English WIP image fresh and load the test save from the
memory card. Don't use a save state: states keep the old catalog code in memory. In
town, open Boltac's catalog. The test save has every item marked seen.

**What to look for:** the parchment lining up at the picture's edges, the item looking
right at its size (above all the shrunk ones), nothing of the item cut off, and the
description's last line fully visible.

**Route:** seven lists, in menu order, each visited once: Weapons > Staves, Weapons >
Spears, then Armor > Robes, Chain and Plate, then Helms, then Other > Cloaks. In each
list, scroll down from the top; the # column is the position in the list. Lines is the
description's current length (5 is the limit).

## 1. Weapons > Staves (1 items: #1)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Staff | trimmed | 5 | |

## 2. Weapons > Spears (18 items: all 19 except #15)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Rod | moved up | 5 | |
| 2 | Lance | shrunk 1% | 5 | |
| 3 | Red Spear | moved up | 4 | |
| 4 | Nagamaki | shrunk 2% | 4 | |
| 5 | Cross Spear | trimmed | 4 | |
| 6 | Partisan | moved up | 4 | |
| 7 | Halberd | moved up | 5 | |
| 8 | Joan's Lance | moved up | 4 | |
| 9 | Hayai Bo | moved up | 3 | |
| 10 | Rokkaku Jo | moved up | 4 | |
| 11 | Faust Halberd | moved up | 4 | |
| 12 | Katakama Yari | shrunk 1% | 3 | |
| 13 | Nyoi Bo | trimmed | 5 | |
| 14 | Tombogiri | moved up | 4 | |
| 16 | Scythe Of Death | shrunk 3% | 4 | |
| 17 | Benkei's Glaive | shrunk 3% | 5 | |
| 18 | Devil Slayer | moved up | 5 | |
| 19 | Holy Lance | trimmed | 5 | |

## 3. Armor > Robes (14 items: all 15 except #2)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Robes | shrunk 2% | 4 | |
| 3 | Displaser Robe | shrunk 5% | 5 | |
| 4 | Shinobi's Robe | shrunk 4% | 3 | |
| 5 | Cursed Robe | shrunk 4% | 4 | |
| 6 | Emerald Robes | shrunk 3% | 5 | |
| 7 | Sapphire Robes | shrunk 3% | 6 (over, known) | |
| 8 | Scarlet Robes | shrunk 3% | 4 | |
| 9 | Worst Robe | moved up | 4 | |
| 10 | Lich's Robe | shrunk 5% | 5 | |
| 11 | Faerie's Robe | shrunk 4% | 5 | |
| 12 | Angel's Robe | **shrunk 9%** | 4 | |
| 13 | Robe Of Pope | shrunk 5% | 5 | |
| 14 | Perfection Dougi | trimmed | 5 | |
| 15 | Ninja Garb | shrunk 5% | 5 | |

## 4. Armor > Chain (6 items: all 6)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Chain Mail | trimmed | 3 | |
| 2 | Shiny Chain Mail | **shrunk 6%** | 4 | |
| 3 | Cursed Chain Mail | **shrunk 7%** | 4 | |
| 4 | Cold Chain Mail | shrunk 3% | 4 | |
| 5 | Fire Chain Mail | shrunk 4% | 4 | |
| 6 | Strongest Chain Mail | trimmed | 4 | |

## 5. Armor > Plate (8 items: all 8)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Cursed Plate | shrunk 1% | 3 | |
| 2 | Plate Mail | shrunk 5% | 4 | |
| 3 | Armor Of Neutral | trimmed | 5 | |
| 4 | Armor Of Evil | trimmed | 4 | |
| 5 | Silver Mail | trimmed | 4 | |
| 6 | Mythril Plate | trimmed | 5 | |
| 7 | Armor Of Master | trimmed | 4 | |
| 8 | Armor Of Lords | shrunk 5% | 5 | |

## 6. Helms > Helms (2 items: #4, #12)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 4 | Helm Of Evil | trimmed | 5 | |
| 12 | Demoniac Helm | trimmed | 5 | |

## 7. Other > Cloaks (6 items: #1, #2, #3, #4, #6, #8)

| # | Item | Picture | Lines | Check |
|---|---|---|---|---|
| 1 | Shadow Cloak | shrunk 5% | 5 | |
| 2 | Night Cloak | shrunk 5% | 4 | |
| 3 | Darkness Cloak | shrunk 4% | 5 | |
| 4 | Cape Of Hide | trimmed | 4 | |
| 6 | Cloak Of Capricorn | trimmed | 5 | |
| 8 | Cape Of Hide' | shrunk 5% | 4 | |

Bold marks the items shrunk 6% or more, the likeliest to look off.
