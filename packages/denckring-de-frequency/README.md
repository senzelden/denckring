# denckring-de-frequency

German frequency bands for [denckring](https://github.com/senzelden/denckring),
from the [Leipzig Corpora Collection](https://corpora.uni-leipzig.de/).

```console
pip install denckring[de-frequency]
```

It supplies one capability, `lexicon.graded_words`: a table pairing each word
with a band from 10 to 60, where **larger means less common**. `anagram` needs
it to rank the covers it finds — a search that cannot tell a common word from a
rare one returns its answers in no useful order — and without this distribution
German `anagram` can check but not generate.

It registers no entry point. `denckring-de-data` owns the `de` language and its
`pack()` factory composes this distribution in when it is importable, because
`denckring` refuses two packs claiming one language (ADR 0013, ADR 0030).

## Why a separate distribution

German data now arrives under three licences: `denckring-de-data` is CC0
Wikidata, `denckring-de-wiktionary` is CC BY-SA Wiktionary, and this is CC BY
Leipzig. ADR 0013 quarantines a data licence in its own distribution, and CC BY
cannot join the CC0 package — CC0 waives rights where CC BY requires
attribution, so merging them would make that package's declaration false.

It is deliberately independent of `denckring-de-wiktionary`, so German `anagram`
does not pull in 6.5 MB of pronunciations it never reads.

## Rebuilding the table

```console
uv run python packages/denckring-de-frequency/scripts/build_frequency.py
```

Downloads the corpus once into `~/.cache/denckring-dumps` and writes
`graded_words.txt.gz`. See ADR 0038 for the case rule the build turns on, and
for the two costs it accepts.
