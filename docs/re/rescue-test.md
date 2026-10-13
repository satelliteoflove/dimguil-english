# The NPC rescue fees, tested in natural play

When a party is wiped in the maze, Guy's, Balbo's or Fontana's party can offer to carry
the bodies back to town. C-talk.md §5 read the fees from the code: Guy's party takes all
the rescued characters' gold, Balbo's all their items, Fontana's half the gold and every
other item. This test plays all three offers through in the emulator, reading the roster
before and after each step.

Run 2026-10-13. Scripts, states, logs and screenshots are in `rips/re/work/P3-rescue2/`
(not tracked). The earlier attempt in `rips/re/work/P3-rescue/` stalled at the pillar
fights and is superseded.

## Summary

| Party | Code (C-talk.md §5) | Seen |
|---|---|---|
| Guy | every member: gold to 0, area 0xff | the same: 357, 125 and 125 G taken; items, status and x/y untouched |
| Balbo | every member: all ten item slots emptied (0xffff, state 0xff), area 0xff | the same: 4 and 6 items taken (the third member had none left); gold untouched |
| Fontana | every member: gold halved, slots "1, 3, 5, 7, 9" emptied, area 0xff | gold halved, rounding down (125 → 62); the slots emptied are the **first, third, fifth...** (0, 2, 4, 6, 8 counting from 0), then every pack is compacted |

- The code's fees are right, apart from the Fontana slot numbering, which C-talk.md §5
  (and engine-notes.md, README.md) had one off. Corrected there.
- **Bug: a rescued party stays a rescue candidate.** Guy's party offered to rescue the
  same party again in the same meeting and at a later one, and Fontana's in the same
  meeting, taking the fee again: Fontana's repeat halves the gold again and takes more
  items. Balbo's scan is the same code. See below.
- After Yes nothing more is said; the bodies just turn up in the Temple's list, as the
  offers promised.
- No and Look for Companions leave everything as it was.

## Method

- **Build.** The published English WIP, `Wizardry - Dimguil (English WIP).bin`, md5
  `06c9523ad68909f36dfc9746f6fb7c3a` (version.txt a8df9cc, 2026-10-13T13:16:55; the
  harness calls the same disc 2540ecc). Copied to `P3-rescue2/dimguil-en.bin` before the
  first boot, so every state in the chain was made on this copy.
- **Standard.** Button presses and save states from ordinary play only, from power-on.
  RAM was read, never written, anywhere in the chain. The only hooks were the harness's
  text capture (a breakpoint on `text_expand` and a write watch on the text buffer),
  which only observe.
- **Setup by the play harness.** `chain.py` runs `scripts/harness` (imported, not
  edited) from power-on on the copy, with no regression cases added: party creation,
  Grounds training, the four pillars, then walkthrough chapter 2. Chain `ga` (seed 201,
  variant 0) did chapters 1-2 in 76 minutes. Chain `gv` is the harness's chapter 2 run
  from a branch of `ga`'s chapter 1 end, with the victims already wiped (below).
- **The test steps** are small scripts, each loading the previous step's state and
  saving its own: `g1_victims.py` to `g7_later.py` (Guy), `b1_victims.py` and
  `bf_case.py` (Balbo, Fontana), `f_reoffer.py`. `rt.py` holds the helpers: roster and
  party-table reads, a chase that walks onto an NPC party's token, and a talk driver
  that picks Talk at the menu, declines sales and stops at a given `talk_state`,
  screenshotting every page shown while `talk_state` is 0x41-0x43. Each step appends
  its roster snapshot to `guy/log.jsonl` or `bf/log.jsonl`. `lines.py` prints every NPC
  line a log saw, Japanese and English.
- **RAM read**: roster (0x8007d708, 0xd0 each: +0x0e status, +0x1c gold, +0x20 items,
  +0x34 item states, +0x7a area/x/y), the party table (0x8008f8c8), the roamer tokens
  (types 0x8005de20, x/y 0x8008b650/0x8008b660, party 0x800879d0), npc_flags 0x80079754,
  progress_bits 0x8007986c, talk_state 0x8007981c.
- **The victims** are always the three premade characters the harness leaves in the
  tavern: Uranus, Jupiter and Mars (roster 0, 2, 4; Neutral, level 5). They start with
  no gold, so they got some by ordinary means (Pool Gold, selling LEATHER GLOVES at
  Boltac's for 250 G). Then they set out and every member chose Parry every round until
  the party was wiped on the Grounds.
- **Party B** (the rescuers) is the harness's party: Venus, Earth and Mercury for Guy,
  so there was room to pick up three bodies; all six for Balbo and Fontana.

## Guy's case

Guy's first meeting at the Shrine door (npc_flags bit 0x15) was already done after
`ga`'s first training trip, and from then on Guy's party has a token on the Grounds
(area 0 allows only Guy, and nothing else is pending there). progress_bits was 2, which
opens the rescue gate (& 0x1e). So the case branches off `ga` there.

| Step | What was done (pad and states only) | State (`guy/`) |
|---|---|---|
| 0 | `ga/goal_03_train_01`: town. Party Venus, Earth, Mercury, Ace, Bea, Cy; Uranus, Jupiter, Mars in the tavern. npc_flags 0x200000 | `g00_src` |
| 1 | Tavern: Cy out, Uranus in, Pool Gold on Uranus (715 G). Everyone out; Uranus, Jupiter, Mars in. Boltac's: Jupiter and Mars sell their LEATHER GLOVES | `g01_victims_town` |
| 2 | Begin Adventure, walk to a fight square, Parry until wiped. Wiped at Grounds (18, 12) in one long fight; the game returns to town | `g02_wiped` |
| 3 | Venus, Earth, Mercury set out. Guy's token (type 1, party 0) was at (20, 15); walked onto it. Greeting, then Talk 11 times: 7 chats, 3 sale offers (declined), then the rescue offer | `g03_met`, `g03_offer` (at the yes/no) |
| 4 | Yes. Leave, walk home, Temple → Heal Character | `g04_yes_maze`, `g04_yes_town` |
| 4b | From the offer: Yes, then Talk again in the same meeting | `g04b_reoffer` |
| 5 | From the offer: No. Leave | `g05_no_maze` |
| 6 | From step 5: walk to (18, 12), START → Look for Companions, take all three, walk home | `g06_on_square`, `g06_lfc_done`, `g06_lfc_town` |
| 7 | From step 4, home after Yes: Venus, Earth, Mercury go back out and meet Guy's party again | `g07_later_offer` |

The victims, status 0x80 (dead) from the wipe on:

| | Uranus | Jupiter | Mars |
|---|---|---|---|
| In town, before | 715 G; LONG SWORD, LEATHER SHIELD, PLATE MAIL, LEATHER SALLET, LEATHER GLOVES, BUSKINS | 250 G; LANCE, BREAST PLATE, LEATHER SALLET, BUSKINS | 250 G; BLOW GUN, PADDED LEATHER, LEATHER SALLET, BLACK BOOTS, LUTE, ANGEL FLUTE |
| After the wipe | 357 G; LONG SWORD, PLATE MAIL | 125 G; all four | 125 G; all six |
| **After Yes** | **0 G**, same items, area 0xff, x/y (18, 12) kept | **0 G**, same items, area 0xff | **0 G**, same items, area 0xff |
| After No | unchanged, area 0 | unchanged | unchanged |
| After Look for Companions | unchanged, in party B | unchanged | unchanged |

- **The fee is the code's.** Yes set each member's gold to 0 and area to 0xff. Items,
  item states, status, HP and the stored x/y were untouched. Party B's gold didn't move
  (0 before and after): the 607 G just goes.
- **The wipe** halved every member's gold, rounding down (715 → 357), and destroyed four
  of Uranus's six items while Jupiter and Mars kept all of theirs: one member's pack
  rolled, the others untouched (A-maze.md §4, bugs.md 3.1).
- **Where the bodies go.** After Yes the talk goes back to its menu; the "carried to the
  temple" line (SISETU 614) isn't used. Walking home, the Temple's "Help whom?" lists
  Uranus, Jupiter and Mars, Uranus showing 0 G (`guy/yes_temple_list.png`).
- **No** changes nothing (`guy/no_01_ts43.png`).
- **Look for Companions** on (18, 12) listed all three as Dead, and each circle took the
  one under the cursor (`guy/lfc_00_menu.png`, `lfc_01.png` to `lfc_04.png`). Gold and
  items unchanged, and the old party record was freed. At home the Temple listed them
  with their gold, Uranus 357 G (`guy/lfc_temple_list.png`).
- **How often.** Nobody in party B was hurt and every pack had room, so a Talk can give
  a chat, a sale or a rescue. 11 Talks gave 7 chats, 3 sales and the offer; the code's
  odds are 62.5%, 25% and 12.5%.

## Balbo's and Fontana's cases

Both need the three Shrine meetings done (Guy 1F, Balbo 3F, Fontana 4F: npc_flags 0x11,
0x12, 0x14); while any is pending, no random party token goes on areas 1-4. Chapter 2 of
the walkthrough does all three, so the victims were wiped first and the harness then
played chapter 2 with the bodies lying on the Grounds.

| Step | What was done | State (`bf/`) |
|---|---|---|
| 0 | `ga/c1_end`: Shrine 1F, after the Tablet door | `b00_src` |
| 1 | Walk home. Tavern: everyone out; Uranus, Jupiter, Mars in. Boltac's: each sells LEATHER GLOVES (250 G each) | `b01_victims_town` |
| 2 | Begin Adventure, Parry until wiped: Grounds (19, 7). Back in town, the six re-form | `b02_wiped`, `b02_six_town` |
| 3 | `chain.py gv`: the harness plays chapter 2 from there (switches, jade mask, the jewel lift to Underground B3). npc_flags 0x3e0000, progress_bits 0xe. The bodies were untouched through all of it | `b03_c2end` (= `gv/c2_end`) |
| B | `bf_case.py B 1`: the six ride the lift up to 4F and walk down to 3F, where Balbo's token was (8, 9). Walked onto it. Greeting; the first Talk played the introductions, the second the offer. Yes, and No from the same state | `B_met`, `B_offer`, `B_yes`, `B_no` |
| F | `bf_case.py F 2`: on B3 Fontana's token is the only party allowed (Guy and Balbo still have their Underground meetings pending), but it kept landing in, or wandering into, parts of B3 the party can't reach from the lift. After a few trips up to 4F and back it was in reach. The first Talk played the introductions, the second the offer. Yes; No | `F_met`, `F_offer`, `F_yes`, `F_no` |
| F2 | `f_reoffer.py`: from the offer, Yes, then Talk again in the same meeting | `F_reoffer`, `F_reoffer_yes` |

The victims at the offer (after the wipe; status 0x80):

| | Uranus | Jupiter | Mars |
|---|---|---|---|
| Before the wipe | 250 G; LONG SWORD, LEATHER SHIELD, PLATE MAIL, LEATHER SALLET, BUSKINS | 250 G; LANCE, BREAST PLATE, LEATHER SALLET, BUSKINS | 250 G; BLOW GUN, PADDED LEATHER, LEATHER SALLET, BLACK BOOTS, LUTE, ANGEL FLUTE |
| At the offer | 125 G; nothing (the wipe destroyed all five) | 125 G; all four | 125 G; all six |
| **Balbo, Yes** | 125 G; nothing; area 0xff | **125 G; nothing** (all ten slots 0xffff, states 0xff); area 0xff | **125 G; nothing**; area 0xff |
| **Fontana, Yes** | **62 G**; nothing; area 0xff | **62 G**; BREAST PLATE, BUSKINS | **62 G**; PADDED LEATHER, BLACK BOOTS, ANGEL FLUTE |
| Fontana, second Yes (bug) | **31 G** | **31 G**; BUSKINS | **31 G**; BLACK BOOTS |
| No (either) | unchanged, area 0 | unchanged | unchanged |

- **Balbo** takes every item, equipped ones included, and leaves the gold. Status, x/y
  untouched.
- **Fontana** halves the gold, rounding down, and empties the first, third and fifth
  slots: Jupiter lost LANCE and LEATHER SALLET (slots 0, 2), Mars lost BLOW GUN, LEATHER
  SALLET and LUTE (slots 0, 2, 4). What's left is compacted to the front. The first slot
  is usually the equipped weapon, so Fontana nearly always takes it. Her Yes compacts
  every roster record's pack (`pack_compact` over the roster): party B's packs only had
  some empty slots' state bytes rewritten.
- Party B's gold and items didn't change in either case.

## Bug: a rescued party stays a rescue candidate

The Yes moves the bodies to town but leaves their party record in the party table. The
rescue scan in all three handlers only checks that every member's status is above 0x1f,
not where they are. [code: `talk_guy` 0x800b5694, `talk_balbo` 0x800c7264,
`talk_fontana` 0x800cf8c0, the scans before state 0x41] So the same party is offered
again:

- **[emu] Same meeting, Guy.** After Yes, five more Talks brought the same offer, word
  for word (`guy/reoffer_*.png`). A second Yes took nothing; the gold was already 0.
- **[emu] Later meeting, Guy.** From home after the Yes (the record still there), party
  B went back out, met Guy's party again, and the third Talk offered to rescue the same
  party (`guy/later_*.png`).
- **[emu] Same meeting, Fontana.** After Yes, three more Talks brought her offer again.
  A second Yes halved their gold again (62 → 31) and emptied the first and third slots
  of the compacted packs (Jupiter's BREAST PLATE; Mars's PADDED LEATHER and ANGEL FLUTE)
  (`bf/F_reoffer_*.png`).
  Each repeat costs half the gold and roughly half the items, for bodies already at the
  Temple.
- **[code] When it clears.** The town's cleanup that frees a party with a member in town
  (JOUKA `town_main` 0x800a2198) runs only on its other branch: 0x800799a1 = 0xfd, set by
  MCARD's continue-from-save (0x800acd78) and "Go On with Another Party" (0x800b00c4),
  or 0x80079567 = 1, set by MAIN's `main` when a party is wiped. So the record goes the
  next time a party is wiped or a game is loaded. A plain walk home doesn't clear it:
  the record was still there in town in Guy's steps 4 and 7. The offers also stop once
  any member is raised (status 0 isn't above 0x1f).
- **A fix** would free the party record on Yes (id -1, count 0, members -1), as Look for
  Companions does for a party it empties. Not made. It's for bugs.md.

fallen-parties.md's table says the town cleanup runs on entering town; it runs only on
those three paths (after a wipe, a load, or "Go On with Another Party").

## The English, checked against the Japanese

Every NPC line the test showed, Japanese from the original disc
(`rips/clean/dimguil/DATA06`), English from `translations/`. No text was changed.

### The offers, and whether they fit the fee

- **Guy (1:163-166).** Accurate. 163's "as a favor to you" (我々の好意として) sets up
  165's "We'll just help ourselves to our fee" (いただけるところから,いただきますから),
  and the fee really is everything they can take in gold, so the joke lands on the
  truth. 163 is stiffer than Guy usually sounds ("Should you wish it, we would be
  pleased"), but the Japanese turns formal there too (差し上げる), and the mock courtesy
  suits the setup. 164 "Accept the favor?" and 166 are fine.
- **Balbo (2:142-145).** Accurate, and the tone fits: he takes every item, and 144 says
  so ("that lot had some mighty fine gear on 'em. Finders keepers, right?"; "Finders
  keepers" is an addition, decided 2026-10-10). One question: 142 is in the leaders'
  stiff maze register (我々, 君たち, かい, のだが), and translation-notes.md's rule for that
  register keeps Balbo's words but "the g's stay on". 142 has "doin'", "'em" and "ya".
  Chris rebroke 142 himself, so this may be settled; flagged in case it isn't.
- **Fontana (3:151-154).** Accurate on the facts, but 153 doesn't fit the fee. The
  English is all kindness: "You're a soft-hearted bunch, too... We'll take good care
  of them." The Japanese has the wink npc-review.md suspected: お人好し is closer to
  "trusting" or "easy marks", and 悪いようにはしませんから is the stock "we won't do you
  wrong", said by someone about to. With the fee seen (half the gold and the first,
  third, fifth items, which means the weapon), the irony is real, and the English
  gives the player no hint of it. Guy's and Balbo's lines both own up; Fontana's is the
  one that hides it. 151's "just between us" (ここだけの話) may be part of the same act.
  152 and 154 are fine.

### Everything else shown

Greetings, introductions, chats and the sale offers: NPC_MES1 16, 17, 47, 59, 167,
168, 173, 257-260, 283; NPC_MES2 2, 96-100, 270; NPC_MES3 1, 5, 111-115, 220-236, 277,
282. All accurate, in voice, with no issues found. Lilia's "seventeen and holding"
(3:227, ピチピチの17才) is a known, decided rendering.

## Screenshots

In `rips/re/work/P3-rescue2/`. Each `*_NN_tsXX.png` is a page just before the press
that turned it, XX the talk_state (41 the offer, 43 the reply).

| Case | Files |
|---|---|
| Guy, setup | `guy/g01_victims_town.png`, `guy/g02_wiped_town.png` |
| Guy, offer | `guy/offer_01_ts41.png`, `guy/offer_02_ts41.png`, `guy/offer_yesno.png` |
| Guy, Yes | `guy/yes_01_ts43.png`, `guy/yes_02_ts43.png`, `guy/yes_temple_list.png` |
| Guy, No | `guy/no_01_ts43.png` |
| Guy, Look for Companions | `guy/lfc_00_menu.png`, `guy/lfc_01.png` to `guy/lfc_04.png`, `guy/lfc_temple_list.png` |
| Guy, repeat offers (bug) | `guy/reoffer_01_ts41.png`, `guy/reoffer_02_ts41.png`, `guy/reoffer_yesno.png`, `guy/later_01_ts41.png`, `guy/later_02_ts41.png`, `guy/later_yesno.png` |
| Balbo | `bf/B_offer_01_ts41.png` to `bf/B_offer_03_ts41.png`, `bf/B_offer_yesno.png`, `bf/B_yes_01_ts43.png`, `bf/B_no_01_ts43.png` |
| Fontana | `bf/F_offer_01_ts41.png` to `bf/F_offer_03_ts41.png`, `bf/F_offer_yesno.png`, `bf/F_yes_01_ts43.png`, `bf/F_yes_02_ts43.png`, `bf/F_no_01_ts43.png`, `bf/F_no_02_ts43.png` |
| Fontana, repeat offer (bug) | `bf/F_reoffer_01_ts41.png` to `bf/F_reoffer_03_ts41.png`, `bf/F_reoffer_yesno.png` |

`superseded/` holds first runs and a dry run, not cited here (its README says what).

## Open questions

- **The repeat offer.** Fix it (free the record on Yes), and does it go in bugs.md
  group 1? For Fontana it's a real loss, repeatable until a member is raised, another
  party is wiped, or a game is loaded.
- **Fontana's 153.** Does the English want the wink back ("You're a trusting bunch...
  Don't worry, we won't do you wrong")? That's a review-tool scene, not a fix here.
- **Balbo's 142.** "doin'", "'em", "ya" against the leaders' maze-register rule; settled
  or not?
- **Not tested:** a rescue when two wiped parties exist (the code picks one at random),
  candidates that are paralyzed or stoned rather than dead, and the Temple raising a
  rescued character.
