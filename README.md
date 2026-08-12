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
$ denckring check lipogram --lang de gedicht.txt
$ denckring status
31 catalogued · 12 implemented · 12 validated
```

Every procedure pairs a generator with a validator, and the acceptance criterion is
intrinsic: a lipogram either contains the forbidden letter or it does not. Nothing has
to be invented to test it. `check` is mandatory for every procedure; `apply` is optional
and only meaningful for the constructive ones.

## Install

```console
pip install denckring          # English and German, no data files
pip install denckring[en]      # + exact syllable counts from a pronouncing dictionary
pip install denckring[fr]      # French (not yet released)
```

The `[en]` extra improves existing procedures rather than enabling new ones. Without it
syllables are estimated from spelling and every report says how many words were guessed;
with it, that number goes to zero for words the dictionary knows.

German ships in core because the twelve procedures below need no lexicon. It registers
through the `denckring.lang` entry-point group — the same path a third-party pack takes.

## What's here

Batch 1 implements the twelve procedures that need no lexicon: `lipogram`,
`univocalic`, `tautogram`, `pangram`, `heterogram`, `palindrome`, `snowball`,
`reverse_snowball`, `prisoners_constraint`, `beau_present`, `acrostic` and `telestich`.
The catalogue lists many more, sourced and awaiting implementation — see
`denckring list --status catalogued`.

## What can be checked

Not every procedure in the catalogue can be graded by a program, and the catalogue says
which. `checkability: self` means decidable from the text alone; `source` means it needs
the text it was made from, supplied as `--source`; `none` means no computable acceptance
criterion exists — `canada_dry` is *defined* as having no operative constraint, and a
calligram's shape is not something code judges. Those rows are catalogued because the
forms belong in an honest survey, and `denckring status` counts them separately rather
than reporting a gap that can never close.

## Reports

`check` returns a `Report`: `satisfied`, a continuous `score` in `[0, 1]`, a list of
`violations` with character offsets, and free-form `metrics`. The score is monotone in
violation count and `satisfied` is exactly `score == 1.0`, so a caller driving a retry
loop can tell whether a text missed by one word or by fifty.

## Languages

Language packs declare capabilities; procedures declare what they require. Asking for a
language whose pack is not installed, or a procedure whose requirements that pack does
not meet, raises rather than quietly returning an approximate answer.

Whether `ä` counts as `a` is an editorial decision rather than a library constant, so it
is a parameter: `fold_diacritics` defaults to true and can be turned off per call. Glyph
questions never fold — *Masse* satisfies the prisoner's constraint and *Maße* does not,
because a written `ß` carries an ascender.

## Three ways in

```python
from denckring import get

get("lipogram").check(text, lang="en")  # 1. library
```

```console
denckring check lipogram --json text.txt          # 2. CLI, exits 1 when unsatisfied
denckring show lipogram --json                    # 3. stable JSON for non-Python callers
```

## Documentation

The [gallery](https://senzelden.github.io/denckring/gallery/) has a page per catalogued
procedure, generated from the catalogue and the golden fixtures — so every worked
example on it is one the test suite enforces, and none of it can drift. Build it
locally with:

```console
uv run python scripts/build_gallery.py && uv run mkdocs serve
```

## Contributing

One module per procedure, `check` mandatory. Start with `denckring new <id>`, which
scaffolds the module, test, strategy, golden fixture and catalogue row. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Scope of the name

The *Fünffacher Denckring der Teutschen Sprache* (Harsdörffer, 1651) is one device among
the hundreds catalogued here, not the whole subject. Werkzeug is not only about tools
either. Searching for `oulipy` will also find this package.

## The catalogue as data

The catalogue is 145 sourced procedures and is a contribution in its own right — useful
to someone who will never install the package.

```console
denckring search rhopalic            # finds snowball by its alias
denckring list --family form         # the prosodic and stanzaic entries
denckring catalogue export --format json --output catalogue.json
denckring catalogue export --format csv
```

Every entry records **how** its source was established, which is the field that makes
the dataset trustworthy: `primary` names an author, work and year the catalogue stands
behind; `reference` means the form is attested in a standard work — the *Oulipo
Compendium*, Borgmann's *Language on Vacation*, *Word Ways* — rather than traced to an
origin; `traditional` means no single origin exists to name. A `reference` row is not a
weaker `primary`; it is an honest statement that the origin is not established.

Entries are filed under one of eight families — `letter`, `word`, `syntax`, `form`,
`permutation`, `procedural`, `translation`, `visual` — and carry the other names each
form travels under, so a search for `isogram` finds `heterogram`.

## Licence

Code is MIT. The catalogue is CC BY 4.0 — see [LICENSE-DATA](LICENSE-DATA) for the
attribution string and what the licence does and does not cover.
