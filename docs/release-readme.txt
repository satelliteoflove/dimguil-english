Wizardry: Dimguil English translation, {version}
https://github.com/satelliteoflove/dimguil-patcher

This patch translates the Japanese PlayStation release of Wizardry: Dimguil
(SLPS-02691) into English. It's for the Rev 1 disc only.


What's in this version
----------------------

{notes}


Patching
--------

You need a redump-style copy of the Rev 1 disc: one .cue file and three .bin
files. Only Track 1 gets patched.

1. Apply {patch} to
   "Wizardry - Dimguil (Japan) (Rev 1) (Track 1).bin". Any xdelta patcher
   will do: xdelta UI or Delta Patcher on Windows, xdelta3 on the command
   line, or Rom Patcher JS in a browser
   (https://www.marcrobledo.com/RomPatcher.js/).
2. Give the patched file the same name as the original, or change the first
   FILE line in the .cue to match. Leave Track 2, Track 3 and the rest of the
   .cue alone.
3. Load the .cue in your emulator.

Track 1 before patching:
  CRC32 {src_crc}
  MD5   {src_md5}
  SHA-1 {src_sha1}

Track 1 after patching:
  CRC32 {dst_crc}
  MD5   {dst_md5}
  SHA-1 {dst_sha1}

If the patcher refuses your file, it's most likely the original 2000
pressing rather than Rev 1, or a dump that was merged into a single .bin.


Origins
-------

{notice}


License
-------

The patch and its source are GPL-3.0. The source is at the address at the
top of this file.
