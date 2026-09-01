# denckring-fr-data

French lexicon and prosody data for [denckring](https://github.com/senzelden/denckring):
word membership, an ordered noun list, frequency bands, glosses, a syllable and
phoneme table, and an aspirated-*h* list.

```console
pip install denckring[fr]
```

Installing this gives the French pack `lexicon.words`, `lexicon.nouns`,
`lexicon.glosses`, `lexicon.graded_words`, `syllables`, `syllables.dictionary`,
`syllables.heuristic` and `phonemes`. The lexicon capabilities are what
`charade`, `semordnilap`, `word_square`, `n_plus_7`, `s_plus_7`, `tmesis`,
`word_ladder`, `kangaroo_word` and the two definitional rows need in order to
run in French — and what `apply anagram` needs in order to generate in it. The
prosody capabilities, plus the line-level elision rules `FrenchDataPack`
overrides `line_syllables` with, are what the 23 syllabic rows
(`alexandrine`, `syllable_count`, `rhyme_scheme`, `haiku`, `hemeling`, and the
rest — ADR 0034) need in order to run in French. Without this package, all of
it raises `MissingCapability` for `fr`, exactly as for any unmet capability.
French still has no lexical stress, so the 18 rows that need `stress` stay
blocked regardless — see ADR 0034 D3.

**125,653 syllable/phoneme rows and 3,370 aspirated-*h* entries**, alongside
the lexicon: 46,947 lemmas, 48,234 noun forms and a Wiktionary gloss slice.
Both sources are **CC BY-SA 4.0** — attribution *and* share-alike — Lexique
3.82 for the lexicon and the prosody table, French Wiktionary for the glosses
and the aspirated-*h* list. See `LICENSE-LEXIQUE` and `LICENSE-WIKTIONARY`.
Regenerate the vendored files with `scripts/build_lexicon.py`.

Accents are preserved rather than folded. `côte` and `cote` are different words,
and whether they should be treated alike is a decision ADR 0009 leaves to the
procedure, not to the lexicon.

The French line count is **estimated, never exact** (ADR 0034 D4): a final
mute *e* elides or counts depending on what follows it, and classical
diérèse is not decidable from spelling alone. Every syllabic report carries
`estimated_words` accordingly.
