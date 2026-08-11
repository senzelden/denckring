# denckring

A library of experimental writing procedures — lipograms, snowballs, acrostics and
several hundred more — where **the validator is the eval**.

```python
from denckring import check

report = check("lipogram", "A small conforming bit of writing", forbidden="z")
print(report.satisfied, report.score)
```

```console
$ denckring check snowball poem.txt
$ denckring status
31 catalogued · 12 implemented · 12 validated
```

Every procedure pairs a generator with a validator, and the acceptance criterion is
intrinsic: a lipogram either contains the forbidden letter or it does not. Nothing has
to be invented to test it. `check` is mandatory for every procedure; `apply` is optional
and only meaningful for the constructive ones.

## Install

```console
pip install denckring          # English, no data files
pip install denckring[de]      # German (not yet released)
pip install denckring[fr]      # French (not yet released)
```

## What's here

Batch 1 implements the twelve procedures that need no lexicon: `lipogram`,
`univocalic`, `tautogram`, `pangram`, `heterogram`, `palindrome`, `snowball`,
`reverse_snowball`, `prisoners_constraint`, `beau_present`, `acrostic` and `telestich`.
The catalogue lists many more, sourced and awaiting implementation — see
`denckring list --status catalogued`.

## Reports

`check` returns a `Report`: `satisfied`, a continuous `score` in `[0, 1]`, a list of
`violations` with character offsets, and free-form `metrics`. The score is monotone in
violation count and `satisfied` is exactly `score == 1.0`, so a caller driving a retry
loop can tell whether a text missed by one word or by fifty.

## Languages

Language packs declare capabilities; procedures declare what they require. Asking for a
language whose pack is not installed, or a procedure whose requirements that pack does
not meet, raises rather than quietly returning an approximate answer.

## Three ways in

```python
from denckring import get

get("lipogram").check(text, lang="en")  # 1. library
```

```console
denckring check lipogram --json text.txt          # 2. CLI, exits 1 when unsatisfied
denckring show lipogram --json                    # 3. stable JSON for non-Python callers
```

## Contributing

One module per procedure, `check` mandatory. Start with `denckring new <id>`, which
scaffolds the module, test, strategy, golden fixture and catalogue row. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Scope of the name

The *Fünffacher Denckring der Teutschen Sprache* (Harsdörffer, 1651) is one device among
the hundreds catalogued here, not the whole subject. Werkzeug is not only about tools
either. Searching for `oulipy` will also find this package.

## Licence

Code is MIT. The catalogue in `src/denckring/data/catalogue.yaml` is CC BY 4.0, with
per-entry source attribution, and is intended to be useful on its own.
