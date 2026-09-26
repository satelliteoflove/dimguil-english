# Building the patched image

You need Linux (or something close to it), a JRE 21+, Python 3 with Pillow,
[armips](https://github.com/Kingcom/armips) and
[mkpsxiso](https://github.com/Lameguy64/mkpsxiso) (which includes dumpsxiso). The
last two are easiest built from source.

You also need your own Rev 1 image. Track 1 should have the md5
`9eeb5c508abb23c0e3538108b7755890`.

Extract it once:

```sh
dumpsxiso -l -x rips/clean/dimguil -s rips/clean/dimguil.xml "<Rev 1 image>.cue"
```

Then build:

```sh
./scripts/build.sh
```

The patched image ends up at `rips/iso/dimguil-en.cue`. Set `ARMIPS` and `MKPSXISO`
if those tools aren't on your PATH. The header of `scripts/build.sh` walks through
the steps.

The committed translation files have the Japanese `source` text redacted, as they
were upstream. The build dumps the Japanese script from your own disc and puts it back
in a staging copy before encoding, so untranslated strings stay Japanese instead of
turning into "NA".
