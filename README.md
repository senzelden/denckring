# denckring

A library of experimental writing procedures — lipograms, snowballs, acrostics and
a hundred and fifty more — where **the validator is the eval**.

```python
from denckring import check

report = check("lipogram", "A small conforming bit of writing", forbidden="z")
print(report.satisfied, report.score)
```

```console
$ denckring check snowball poem.txt
$ denckring check lipogram --lang de gedicht.txt
$ denckring status
153 catalogued · 127 implementable · 118 implemented · 118 validated · 26 not mechanically checkable
```

Every procedure pairs a generator with a validator, and the acceptance criterion is
intrinsic: a lipogram either contains the forbidden letter or it does not. Nothing has
to be invented to test it. `check` is mandatory for every procedure; `apply` is optional
and only meaningful for the constructive ones.

## Install

```console
pip install denckring          # English and German, no data files
pip install denckring[en]      # + a pronouncing dictionary and a noun lexicon
pip install denckring[de]      # + a word lexicon and a noun list
pip install denckring[fr]      # French (not yet released)
```

The `[en]` and `[de]` extras improve or unlock procedures rather than changing the
language itself. Without `[en]`, syllables are estimated from spelling and every report
says how many words were guessed; with it, that number goes to zero for words the
dictionary knows. Without `[de]`, `charade`, `semordnilap`, `word_square`, `n_plus_7`
and `s_plus_7` raise `MissingCapability` for German; with it, they run.

German ships in core because the procedures that need no lexicon work for it
unchanged, and it is a built-in default exactly like English (ADR 0022):
`denckring[de]` overrides that default the same way `denckring[en]` overrides
English's, rather than registering through a separate path.

## What's here

A hundred and eighteen of the 153 catalogued procedures are implemented, and every
one of them is validated. Of the rest, 26 have no mechanical acceptance criterion and
are catalogued rather than implemented — see
[What can be checked](#what-can-be-checked) — and the remaining 9 are sourced and
awaiting implementation. `denckring list`
shows what this install can run; `denckring list --status catalogued` shows
everything.

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

## What is stable

`0.x` means the API can change in a minor release, and the changelog says when it does.
Four surfaces are treated as contracts regardless, because things outside this repository
are built on them:

- **Procedure ids.** An id that has shipped does not change meaning. When a row is
  replaced, the old id stays findable through `denckring search` as an alias — though
  `get` resolves ids only, and raises `UnknownProcedure` naming the replacement.
  `multiple_constraint`, which replaced `univocalic_lipogram_pair`, is the precedent.
- **`Report` as JSON** — `procedure`, `satisfied`, `score`, `violations`, `metrics` — and
  the `--json` output of `check`, `show` and `describe` that carries it. Fields may be
  added; the ones already there do not change type or meaning.
- **The catalogue export schema** (`denckring catalogue export`), including the `licence`
  and `attribution` keys the CC BY terms are carried by.
- **The `denckring.lang` entry-point group** and the capability names a pack declares, so
  an installed third-party pack keeps working.

Not stable, and expected to move: violation `rule` strings, `metrics` keys, message
wording, and everything under `denckring.core`. A check's *verdict* is a contract; the
reason it gives for a failure is not one yet.

## Three ways in

```python
from denckring import get

get("lipogram").check(text, lang="en")  # 1. library
```

```console
denckring check lipogram --json text.txt          # 2. CLI, exits 1 when unsatisfied
denckring show lipogram --json                    # 3. stable JSON for non-Python callers
```

## Letting a model use it

A model writing under a constraint can check its own draft instead of guessing,
which is the difference between a haiku it believes is a haiku and one that is.
Two entry points, both over the same core functions, so they cannot disagree
about what a procedure is:

```console
pip install denckring[mcp]    # an MCP server: denckring-mcp
```

The server exposes four tools — `list_procedures`, `describe_procedure`,
`check_text`, `apply_procedure` — with the procedure as a parameter rather than
eighty-six tools, because model performance degrades with tool count. Errors
come back as data (`{"code": "invalid_params", ...}`), never as a traceback a
model cannot act on.

For Claude Code, the skill at
[`skills/denckring/SKILL.md`](https://github.com/senzelden/denckring/blob/main/skills/denckring/SKILL.md)
shells out to the CLI instead, and needs no extra beyond the package itself.

## Documentation

The [gallery](https://senzelden.github.io/denckring/gallery/) has a page per catalogued
procedure, generated from the catalogue and the golden fixtures — so every worked
example on it is one the test suite enforces, and none of it can drift. Build it
locally with:

```console
uv run python scripts/build_gallery.py && uv run mkdocs serve
```

## Where the data lives

Three kinds of thing a procedure can need, and they are handled differently. A **device**
— Harsdörffer's five rings — is the procedure, so it ships with it. A **language pack**
describes a language and ships separately when it carries weight: `denckring[en]` adds a
pronouncing dictionary and a noun lexicon, `denckring[de]` adds a word lexicon and a noun
list. A **corpus** is somebody's collection, so the package carries the loader and you
supply the reading:

```console
denckring check ideenwuerfeln throw.txt --source my-excerpts.json
```

## The explorer

A local browser for the catalogue and a bench for trying procedures on your own text,
kept outside the distribution in [`apps/explorer`](apps/explorer):

```console
uv run --project apps/explorer explorer
```

It lays the catalogue out as a compositor's type case — one compartment per procedure,
filled where a checker exists — builds each parameter form from that procedure's own
`params_schema()`, and marks the offending characters inline using the offsets every
`Violation` carries.

## Contributing

One module per procedure, `check` mandatory. Start with
`uv run python scripts/new_procedure.py <id>`, which scaffolds the module, test,
strategy, golden fixture and catalogue row. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Scope of the name

The *Fünffacher Denckring der Teutschen Sprache* (Harsdörffer, 1651) is one device
among the hundred and fifty catalogued here, not the whole subject. Werkzeug is not
only about tools either. Searching for `oulipy` will also find this package.

## Using the name

The name is reserved — Apache-2.0 grants no trade mark rights (section 6), which is what
keeps a fork from publishing as this project. What that reservation permits, stated so it
can be complied with rather than guessed at: redistribute the package unmodified under
the name freely, say that your work uses or is compatible with denckring freely, and
rename before publishing a modified version. "denckring" in the name of a package you
publish, or on a site presenting your fork as the original, is the line.

## The catalogue as data

The catalogue is 153 sourced procedures and is a contribution in its own right — useful
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

Code is Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE), which every
derivative distribution has to carry. The catalogue is CC BY 4.0 — see
[LICENSE-DATA](LICENSE-DATA) for the attribution string and what the licence does and
does not cover. The code was MIT before 0.1.0; ADR 0024 records why it moved.
