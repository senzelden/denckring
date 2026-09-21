# The 144 (row, language) pairs that run and are not editorially claimed

*Text for a follow-up issue. Not a document this repository publishes — see ADR
0047, whose Consequences point here.*

## What the number is

`meta.languages` is authored editorial scope; `runs_in` is computed from pack
capabilities. Measured over the 126 implemented rows on 2026-09-21 with every
extra installed, before ADR 0047's tranche:

| | en | de | fr |
|---|---|---|---|
| `runs_in` | 126 | 124 | 106 |
| `languages` | 122 | 46 | 14 |

174 pairs ran without being claimed. ADR 0047 closed 30 of them — the French
rows whose own `source:` field is the evidence. **144 remain: de 78, fr 62,
en 4.**

## Why this is not a backlog

Closing a pair means asserting that a form is a form in that language. Nothing
in the capability measurement supports that assertion, and ADR 0015's rule is
that a claim the data does not carry is not made. A sweep that set
`languages: [en, de, fr]` everywhere it runs would make 144 unsourced claims at
once and would make the field a duplicate of `runs_in`, which is derived
precisely so the two cannot collapse into each other.

So the remainder is an open editorial question, and this issue exists to hold it
open rather than to schedule it.

## What would close a row

The test ADR 0047 used, and the one a next tranche should use:

1. The row's own `source:` names a work, author or tradition in that language.
2. The row runs in that language on this install — verified with
   `describe.runnable(meta, lang)`, row by row, not inferred from the group.
3. The row has, or gains, a `names.<lang>` and a `definitions.<lang>`. This is
   enforced twice: `tests/test_catalogue_quality.py` against the YAML and
   `tests/test_declared_language_strings.py` through `describe`.
4. The row has, or gains, a golden case in that language
   (`tests/test_invariants.py::test_every_declared_language_has_a_golden_case`).
   This is the expensive condition and the valuable one: it turns an editorial
   argument into a text the checker has accepted.

A criterion, not a list. ADR 0047's list of thirty was hand-built and missed a
row that met its own test (`villanelle`, below); the criterion would not have.

## Named candidates

- **`villanelle`** — sourced to "Traditional; fixed in its modern shape by Jean
  Passerat (1606)", runs in French, already carries a French name and a French
  definition, declares `[en]`. It meets ADR 0047's test in full and was left out
  only because it was not on that branch's approved list. It needs one French
  golden case and the declaration. Start here.
- **`sestina`** — Arnaut Daniel, 12th century. Troubadour Occitan rather than
  French, so it fails criterion 1 on the strict reading and passes on the loose
  one. Worth deciding explicitly rather than by omission.
- **`single_sentence`** — "the form of Gertrude Stein's and Thomas Bernhard's
  long prose", runs in German, declares `[en]`, and has no German strings. The
  only German near-miss in the catalogue: its source names a German-language
  author but not a German original. The row that decides how strict criterion 1
  is.
- **`ballade`** — François Villon, and as French as a form gets, but it does not
  run in French: it needs `stress`, which French has none of. Blocked
  permanently (ADR 0034, and `.claude/rules/french.md`'s "the 18 are the ceiling,
  not a shortfall"). Listed so nobody re-derives it as an oversight.

## What not to do

- Do not widen `languages` to match `runs_in`. That is the drift `runs_in` was
  derived to prevent.
- Do not declare a language to reach a bigger number. The 18 French rows blocked
  on `stress` are the standing example of a count that must not be moved by
  declaration.
- Do not add a language without its strings and its golden case. Three separate
  guards refuse it, and they refuse it because the fallback to English is silent
  and per field.
