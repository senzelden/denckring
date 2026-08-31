# denckring-de-wiktionary

German pronunciation and gloss data for [denckring](https://github.com/senzelden/denckring),
from German Wiktionary.

```console
pip install denckring[de-wiktionary]
```

Installing this gives the German pack `phonemes`, `stress`, `syllables`,
`syllables.dictionary` and `lexicon.glosses` — every metre, rhyme and verse form
in the catalogue, in German. Without it those procedures raise
`MissingCapability` for `de`, exactly as they do for any unmet capability.

It registers no language pack of its own. `denckring/lang/__init__.py` refuses
two entry points claiming one language, so a second `de` pack could not be
installed beside `denckring-de-data`; that package detects this one instead and
extends its own capabilities when it is importable. ADR 0030 records the cost:
what `GermanDataPack` can do is no longer readable from its class alone.

The data is derived from German Wiktionary and is **CC BY-SA 4.0** — attribution
*and* share-alike, unlike the CC0 data in `denckring-de-data`. That difference is
the whole reason for a fourth distribution. See `LICENSE-WIKTIONARY`.
Regenerate the vendored files with `scripts/build_pronunciations.py`.

Syllable counts and stress are read off the transcription rather than sourced
separately: German Wiktionary's IPA marks primary stress `ˈ` and secondary `ˌ`,
so a stress pattern is derived from the string exactly as the English pack
derives one from CMUdict's digits. `stress` is therefore never present without
`phonemes`.
