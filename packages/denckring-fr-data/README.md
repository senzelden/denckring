# denckring-fr-data

French lexicon data for [denckring](https://github.com/senzelden/denckring):
word membership, an ordered noun list, frequency bands and glosses.

```console
pip install denckring[fr]
```

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses` and `lexicon.graded_words`, which is what `charade`,
`semordnilap`, `word_square`, `n_plus_7`, `s_plus_7`, `tmesis`, `word_ladder`,
`kangaroo_word` and the two definitional rows need in order to run in French —
and what `apply anagram` needs in order to generate in it. Without it those
procedures raise `MissingCapability` for `fr`, exactly as for any unmet
capability.

The data is **CC BY-SA 4.0** — attribution *and* share-alike — from Lexique 3.82
and French Wiktionary. See `LICENSE-LEXIQUE` and `LICENSE-WIKTIONARY`.
Regenerate the vendored files with `scripts/build_lexicon.py`.

Accents are preserved rather than folded. `côte` and `cote` are different words,
and whether they should be treated alike is a decision ADR 0009 leaves to the
procedure, not to the lexicon.

This distribution supplies no prosody. French has no lexical stress, and the
syllable capabilities wait on the line-level counter that chapter 6 tranche B
designs; see ADR 0032 and the chapter spec.
