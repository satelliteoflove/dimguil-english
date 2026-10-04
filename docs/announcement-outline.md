# Release announcement outline

An outline for the v0.8.0 release post, for Chris to write from (checklist item W8). It
is one structure that adapts to each venue: the r/wizardry post, the RetroGameTalk
thread and the GitHub release page. The RHDN description (W7) uses the same order in
the third person. Items marked with a checklist ID depend on that item being settled
first.

## Order

1. **Title.** Game, platform, "English Patch v0.8.0 (Beta)". On RetroGameTalk the
   "[AI-Assisted Translation]" tag goes in the title, as its rules require.

2. **AI disclosure.** First thing in the body, before the pitch. Chris's points from D5:
   what Claude did (machine translation, historical and cultural research, how the game
   uses kanji, hiragana and katakana), what Chris decided (jokes, cultural adaptation,
   the intent and style of the original), and that AI was used throughout, tooling
   included. Then the aim: quality, with the line-by-line review and the full
   playthrough as the evidence. The Japanese-reader question goes here too (D1). Decided
   2026-10-04: the release doesn't wait for a native reviewer, and the care shown in
   item 3 answers the question instead.

3. **Translation approach.** The English sticks to the intent and phrasing of the
   Japanese where possible, and adapts where it has to so the game reads pleasantly and
   is easy to follow. Give examples of both:
   - Care with the language and culture: Guy and Alstron's introduction; Linaria lying
     about her age with the dated "springy as a fresh fish"; the town board modeled on
     the chalkboards at pre-cellphone Japanese train stations; Alstron's Dragon Quest III
     Sage/Bishop class-change reference; other inside jokes kept.
   - Liberties taken: a few concrete cases where the English departs from the Japanese
     and why. Candidates so far:
     - Murphy's Ghost (Catalog 9:24): the English adds "over and over" to spell out the
       joke. He was Wizardry I's famous experience farm, and the Japanese only implies it.

4. **What the game is.** Two or three sentences: Wizardry Gaiden, PS1, 2000, ASCII,
   never released in English. Developer credit waits on F1.

5. **Status.** Beta, playable from start to finish (true once Q3 is done). What has been
   reviewed and what hasn't, with numbers (F6). No "100%" claims beyond what is counted:
   all reachable text is in English, but not all of it has been reviewed twice.

6. **Screenshots.** Four current, native-resolution PNGs plus the title screen (R1). A
   Japanese/English pair of the same screen would show the work at a glance.

7. **What you need.** Your own dump of Rev 1 (Redump #60391) with the Track 1 hashes in
   the post itself. Say plainly that the original pressing (#10368) won't patch (F3).

8. **How to patch and play.** Delta Patcher with checksum validation on, or the
   `xdelta3 -d -s` line (R4). What it's been tested on (F5). Memory-card saves carry
   over between versions, but save states keep the old text (F4).

9. **Download.** A single link to the GitHub release page. Later posts link the RHDN
   entry too, once it exists.

10. **Known issues.** The two or three that matter most, then a link to the full list
   (W5).

11. **Bug reports.** GitHub issues, and what a useful report includes (W6). On
    r/wizardry, the thread works too (D10).

12. **Origins and credits.** The notice from `docs/notice.txt`, required on every page
    that hosts the patch. Remisse's tools named and linked. The tools list, with Claude
    in it (D5).

## From the Tales of Destiny 2 release

The Tales of Destiny 2 PS2/PSP release on RetroGameTalk (2026) shows what a release
post looks like in practice, including updates over several months.

Worth borrowing:

- It says which disc it needs up front, and which version of the disc won't work (the
  Mega Hits reissue).
- It names the patcher and the emulator version it was tested on.
- Its update notes are specific: the scene, the string, what changed and how it was
  tested. One even admits the cause of a crash hasn't been found.
- The forum post is short and the detail lives in the repo (layout rules, glossary,
  build steps).
- It asks for help with specific roles (proofreaders, a font designer).

To do differently:

- Which AI was used came out in a reply, when someone asked, and the reply named a
  different model from the one in the repo's translation script. The disclosure
  belongs in the first post and has to match the repo exactly.
- "100% playable" was posted before anyone had tested it, and the first replies were
  crash reports. Our claim should rest on Chris's playthrough (D2).
- The disc's CRC only appeared in a reply, after someone failed to patch a disc that
  already had a partial translation applied. Put it in the post.
- The post links four download mirrors for each platform. One canonical page is easier
  to keep current.
- Its screenshots were labelled outdated. They should match the build being released.

## Venue notes

- **r/wizardry:** "Wizardry Gaiden" flair; no links to disc images (Rule 5).
- **RetroGameTalk:** "[AI-Assisted Translation]" tag; AI discussion isn't allowed in
  threads (Rule 11). Remisse's original Dimguil thread is on the same site.
- **GitHub release page:** the notes come from the CHANGELOG entry (W3) via
  `scripts/mkrelease.py`, which adds the notice.
- **RHDN:** third person, no "I" or "we".
