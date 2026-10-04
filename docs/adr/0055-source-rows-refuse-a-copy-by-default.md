# 55. Source rows refuse a copy by default

## Context

Fourteen rows check a text against a source, and each of them passed the source itself,
unchanged, as a correct answer: `anagram`, `buchstabwechsel`, `cut_up`, `diastic`,
`homoconsonantism`, `homovocalism`, `lipogrammatic_translation`, `melting_text`,
`mesostic`, `n_plus_7`, `recombination`, `s_plus_7`, `transposal` and
`univocalic_translation`. An anagram of `listen` that is `listen` was satisfied, and so
was an N+7 that displaced nothing. `antigram` alone has always refused it, as
`unchanged`.

denckring-bench found the cost (audit A5). A model asked for a transform could return
its input and score 1.0, so the bench forced strict parameters on every transform it
sent (`FIXED_PARAMS`), and still had to exclude rows it had no parameter to force.
Release 0.3.2 added `allow_identity` to the fourteen rows. Its default was `true`, so
that a patch release moved no verdict, and the field promised the flip this ADR makes.

## Decision

**`allow_identity` defaults to `false` on all fourteen rows.** A text whose letters are
the source's, in the source's order, fails as `unchanged` unless the caller passes
`allow_identity=true`. Case, spacing and punctuation do not make a text new, which is
the comparison `antigram` makes.

**A copy is refused only where the source admits another correct answer** (ruling
R-U2a). Each row states that predicate as the `alternative` it passes to
`source_compare.unchanged`. A one-sentence `recombination`, a one-letter `anagram`, a
one-word `cut_up` or an N+7 source with no listed noun has no answer but the copy, so
the copy passes there under either setting. That is right, because the default exists
to catch a writer who could have done the work and did not. On such a source the copy
*is* the work. Refusing it would make the instance unsatisfiable: every text would
fail, so the verdict would say nothing about the writer. A caller who wants to know
whether a source gives the rule anything to do asks that of the source, not of the
answer.

**`apply` refuses a copy the same way.** Its guard compared the output's text with the
input's, casefolded, so `cut_up` could turn `a.a` into `a a` and return it. Under the
new default its own checker fails that text, which breaks the round-trip property. For
a row whose checker carries the field, the guard now also refuses an output with the
source's letters in the source's order (`source_compare.is_copy`, with the fold that
row's `unchanged` uses). `ApplyParams.allow_identity` still waives it. The two fields
now share their default as well as their name.

## Consequences

This is a breaking change, and that is its purpose. A caller who checked a copy of the
source on one of these rows got `satisfied`, and now gets `unchanged`. The old reading
is one parameter away (`allow_identity=true`), but nothing warns a caller who relied
on it.

A copy of a degenerate source still passes, so `satisfied` does not certify that the
procedure changed anything. That is the cost of keeping every instance satisfiable,
and the predicates carry it. Each row's `alternative` is that row's own claim about
which sources admit another answer. `tests/test_allow_identity.py` holds each claim on
both sides of its edge, but the tests show examples and prove no claim over all
sources. If a predicate says another answer exists where none does, the instance is
unsatisfiable. If it says the reverse, a copy passes that should have been refused.

A refused copy costs one unit of score, not all of it. The verdict is unsatisfied, but
the score stays high on a long source: a copy of `the cat sat on the table` scores
0.857 on `n_plus_7` and `cut_up`, and 0.95 on `anagram`. Read `satisfied`, or the
`unchanged` rule, to tell a copy apart from a near miss. Scoring a copy at zero would
put this row's score on a different scale from every other violation's, and would
make a near copy score far above the copy itself.

`apply` refuses more than before. It now raises `degenerate_output` where it returned
a respaced or repunctuated copy, and a multi-result search drops such candidates. The
guard refuses a copy even where the checker would let it stand, as it always refused
the exact copy. The generator does less than its checker accepts, which is the safe
direction, and the round-trip harness stays green.

**No verdict or score in the golden corpus moved.** Re-measured over all 687
cases, every `satisfied` and every `score` is unchanged. One case's violations changed:
`s_plus_7`'s `elided-source-retyped-unchanged-under-strict` retypes its source, so it
gained `unchanged` beside the `ambiguous_noun_unchanged` it exists to show, and its
score stayed 0. That case is about the strict reading of an ambiguous noun, not about
copies, so it now sets `allow_identity: true` to fail for its own reason alone.
