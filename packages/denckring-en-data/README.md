# denckring-en-data

English pronunciation data for [denckring](https://github.com/senzelden/denckring):
exact syllable counts, and the phoneme tails that rhyme checking will need.

```console
pip install denckring[en]
```

Installing this package replaces the core English pack's spelling heuristic with
dictionary lookups. Nothing in the API changes — the same procedures simply answer more
accurately, and the `estimated_words` metric on every syllabic report drops to zero for
words the dictionary knows.

## Data

Two vendored sources, both redistributed rather than downloaded, so neither
installation nor use touches the network:

- The CMU Pronouncing Dictionary, 135,166 entries, under its BSD-2-Clause licence —
  see `LICENSE-CMUDICT`.
- The Open English WordNet 2024, under its CC BY 4.0 licence — see `LICENSE-WORDNET`.
  `nouns.txt` (56,468 single-word noun lemmas, in dictionary order) and
  `glosses.txt.gz` (78,866 lemmas, 134,298 glosses across every part of speech) are
  both derived from it. `metadata.json` beside the data records the exact version and
  generation date; `scripts/build_lexicon.py` regenerates both files from OEWN alone.

The code in this package is Apache-2.0, like denckring itself. The data is not — see
`NOTICE` for which file carries which terms.
