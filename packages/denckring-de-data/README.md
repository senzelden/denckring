# denckring-de-data

German lexicon data for [denckring](https://github.com/senzelden/denckring):
word membership and an ordered noun list.

```console
pip install denckring[de]
```

Installing this gives the German pack `lexicon.words` and `lexicon.nouns`, which
is what `charade`, `semordnilap`, `word_square`, `n_plus_7` and `s_plus_7` need
in order to run in German. Without it those procedures raise
`MissingCapability` for `de`, exactly as they do for any unmet capability.

The data is derived from Wikidata Lexemes and is CC0 — no attribution, no
share-alike. See `LICENSE-WIKIDATA` for provenance. Regenerate it with
`scripts/build_lexicon.py`; the vendored files are reproducible from that
script alone.

Umlauts and ß are preserved rather than folded. `Bär` and `Bar` are different
words, and whether they should be treated alike is a decision ADR 0009 leaves to
the procedure, not to the lexicon.

Membership is casefolded, which deliberately merges ß and ss spellings (e.g.
Maßen/Massen); the noun list is not casefolded and keeps ß intact.
