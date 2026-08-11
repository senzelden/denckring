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

The CMU Pronouncing Dictionary, 135,166 entries, redistributed under its BSD-2-Clause
licence — see `LICENSE-CMUDICT`. The dictionary is vendored rather than downloaded, so
neither installation nor use touches the network.

The code in this package is MIT, like denckring itself.
