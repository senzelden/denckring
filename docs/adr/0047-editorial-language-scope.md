# 47. Editorial language scope, and the thirty rows their own sources already claim

## Context

The request was to widen German and French support across the catalogue. The
measurement that answers it says the gap is almost entirely *not* a capability
gap, and that the two fields which look like one question are two.

`core/describe.py` already draws the line, and draws it deliberately:

- `meta.languages` is **authored editorial scope** — whether the form is a form
  in that language at all. `wechselsatz` is German by nature, not by capability.
- `runs_in` is **computed from pack capabilities** — whether this install can
  check the row in that language. Derived rather than authored, in its own
  words, "so it cannot drift into the false claim a `[en]` row made once French
  began working".

Measured over the 126 implemented rows on 2026-09-21, with every extra
installed:

| | en | de | fr |
|---|---|---|---|
| `runs_in` (capability) | 126 | 124 | 106 |
| `languages` (editorial) | 122 | 46 | 14 |

**174 (row, language) pairs run today and are not editorially claimed** — fr 92,
de 78, en 4. Capability coverage is close to complete; editorial scope is what
lags, and the two were being read as one number. Closing all 174 would mean
asserting, 174 times, that a form belongs to a language. That is exactly the
unsourced claim ADR 0015 exists to refuse, and no measurement supports it.

## Decision

Widen `languages` only where the row's **own `source` field** is the evidence,
and leave the rest as an open editorial question rather than a backlog.

Thirty rows meet that test for French: their `source` names a French work,
author or tradition, they run in French on this install, and they did not
declare `fr`. `lipogram` is the clearest — its source is Georges Perec, *La
Disparition* (1969), the most famous French lipogram written, and it declared
`[en, de]`. Each of the thirty was verified individually: `describe.runnable`
was asked for `fr` row by row rather than inferred from the tranche, and every
one came back runnable with nothing missing.

Eighteen of the thirty already carried a French name and a French definition and
needed nothing but the declaration. Twelve did not, and the strings were written
before the declaration was made — eleven names and twelve definitions.

The criterion is "the source names a French attestation", not "the form is
French in origin", and five rows sit on the looser half of that: `palindrome`
(Sotades, revived by Oulipo), `snowball` (Ausonius, named by Oulipo), `pangram`
(traditional, catalogued in the *Atlas*), `pantoum` (Malay, adapted into French
in the 19th century) and `assonance_constraint` (the binding device of Old
French and Spanish epic). Each is a form French practises under a French name,
and each is declared on that reading. Stating the reading is the point: a later
reader can disagree with it row by row instead of guessing what rule produced
the set.

**The same test over German-sourced rows returns zero.** Four rows name a
German-language original — `buchstabwechsel`, `denckring`, `wechselsatz`
(Harsdörffer and Kuhlmann) and `ideenwuerfeln` (Jean Paul) — and all four
already declare `de`. German needs no tranche of this kind. That is the
disconfirming half of the measurement, and it is why this decision covers French
alone rather than the two languages the request named.

One near-miss belongs in the record beside that zero. `single_sentence` is
sourced to "the form of Gertrude Stein's and Thomas Bernhard's long prose",
runs in German, and declares `[en]`. Its source names a German-language author
but not a German original — the form is traditional and its other exemplar is
English — so it fails this ADR's test. It is the row a stricter or looser
reading of the criterion would move first, in either language.

## A row may not declare a language it cannot speak

Adding a language to `languages` without a `names` and a `definitions` entry
beside it costs nothing and pushes the row into `Description.untranslated` — the
silent per-field English fallback that the 2026-09-04 sweep made visible
precisely so it would stop being invisible.

That rule was **already guarded at the data level**, and this ADR found the
guard rather than needing one: `tests/test_catalogue_quality.py::
test_every_declared_language_carries_a_name_and_a_definition` has asserted it
over the whole catalogue since nine backlog rows arrived declaring a German they
could not say a word of. So the tranche's twelve French definitions were not
optional politeness; the suite would have refused the declaration without them.

`tests/test_declared_language_strings.py` adds the other half, at the surface a
caller actually sees: for every registered procedure and every language it
declares, `describe(id, lang=...)` must report neither `name` nor `definition`
as untranslated. The two would disagree if `_text` or `_fell_back` stopped
agreeing with the data — a row whose strings are all present but which
`describe` still answers in English passes the YAML check and fails this one.
Both encode the rule rather than today's counts, and the new one was proved red
by giving `clerihew` a `de` it has no strings for.

## Consequences

**Thirty rows gain `fr`, and `languages` for French goes from 14 to 44.**
`runs_in` is untouched: no capability changed, no distribution was added, and
the two numbers moving independently is the distinction working.

**The declaration cost 24 French golden cases, which was not foreseen.**
`tests/test_invariants.py::test_every_declared_language_has_a_golden_case`
requires a fixture in every declared language, so `languages: [..., fr]` is a
promise that the row has been run in French and not merely thought about. Six of
the thirty already had one; the other 24 were written and each was checked
against its own checker — verdict and violation list both — before it was
committed. Three are externally sourced (two traditional French palindromes and
the standard French font-test pangram) and the rest are constructed, marked as
such.

That cost is the decision's best feature rather than its overhead. An editorial
claim backed only by a `source:` line is an argument; the same claim with a
French text the checker accepts is evidence, and the suite now refuses the first
without the second.

**`belle_absente` stopped being the README's example of the distinction**, and
had to. The README said it was `languages: [en]` while running in all three —
true when written, and true only because its `languages` was wrong: the row is
Perec's. `clerihew` replaces it and cannot go the same way, because the form is
English by nature and no French capability will ever make it French.

**The remaining unclaimed pairs stay unclaimed — 144 of them, fr 62 and de 78
and en 4 — and are documented rather than queued.** They are not a coverage gap
and should not be counted as one. `ISSUE-remaining-editorial-scope.md` carries
the text for the follow-up issue: what the remainder is made of, what evidence
would close a row, and why a sweep is the wrong shape for it.

**One row that meets this ADR's own test is not in the tranche.** `villanelle`
is sourced to "Traditional; fixed in its modern shape by Jean Passerat (1606)",
runs in French, already carries a French name and a French definition, and
declares `[en]`. It was not on the list this branch was given and adding it
would have widened an approved scope silently, so it is named here and in the
follow-up issue as the first candidate of the next tranche instead. That a
hand-built list of thirty missed one is the argument for the follow-up issue
being a *criterion* rather than a list.
