# 59. A composite is a list of constraints, and rules and evidence are promised

## Context

`multiple_constraint` took `constraints`, a list of procedure ids, and
`constraint_params`, a table of parameters keyed by id. Keying by id meant no procedure
could appear twice: a text avoiding both `a` and `z` as two separate lipograms, or an
acrostic on one word and a telestich on another of the same row, could not be stated.
The score counted one unit per satisfied constraint, so a pair scored 0, 0.5 or 1. A text
one letter from satisfying both scored as one that broke a constraint everywhere, which
gives a retry loop (ADR 0005) nothing to climb. And the per-constraint scores sat in
`metrics` under `<id>_score`, a key that would collide as soon as an id could repeat.
denckring-bench composes its own constraints rather than build on this row for these
reasons (audit B10).

The bench also reads two things the README called unstable. It maps each
`violation.rule` to its own failure classes, and it decides whether to score a verdict
from `metrics["estimated_words"]` (audit B8). Since 0.3.2 the rule ids are published
through `denckring.rules`, and `Report.evidence` with `Evidence.basis` says which
measurements were looked up and which estimated. 0.4.0 added the `ambiguous` basis
(ADR 0054). Both were documented as "planned for the promise in 0.4.0". A consumer
cannot build on either while a minor release may rename a rule or reshape evidence
without notice.

## Decision

`constraints` is a list of `{"id": ..., "params": {...}}` entries, one per constraint,
in order. `constraint_params` is gone. The same id may appear more than once. The old
shape is refused with `InvalidParams`, and the message rewrites the caller's own call in
the new shape. It is never re-read, so a caller still building the old shape cannot
pass with its parameters dropped. The recursion guard, capability propagation, scope and
hint delegation (ADR 0050) work on the entries as they worked on the ids. A hint
names each constraint by its id and follows with one line per entry, that constraint's
own hint rendered from its `params`; `render_hint`, which renders a caller's own
template, appends the same lines, so a template naming `{constraints}` cannot drop the
letters and words the entries set.

The composite's score is the mean of its constraints' own scores. `satisfied` is true
only when every constraint is satisfied, so `satisfied == (score == 1.0)` still holds: a
mean of scores in `[0, 1]` is 1.0 exactly when each is, and an unsatisfied mean that
rounds to 1.0 in floating point is capped one step below it. Violations keep their rule
strings and are prefixed with their constraint's id in `note`, as before; when an id
repeats, the note names the entry's position too (`lipogram (constraints[1])`), and a
constraint's `InvalidParams` always does. Evidence is not attributed the same way: an
`Evidence.subject` is promised as the word or line itself, so a position suffix would
change what the field means. A composite that repeats an id carries each entry's evidence
unattributed, and `delegates.<i>.*` is where a caller tells the entries apart. `metrics`
carries each constraint's verdict and score in constraint order as
`delegates.<i>.satisfied` (1.0 or 0.0) and `delegates.<i>.score`. These keys are flat
and numbered by position because `Report.metrics` maps names to numbers and is under
the promise; a list of objects there would change its type. The id at position `i` is
the caller's own `constraints[i]`.

The README's "What is stable" takes two more surfaces. First, violation `rule` strings:
a rule published through `denckring.rules(procedure_id)` keeps its name and meaning. A
row may add rules, and removing or renaming one is a breaking change the changelog
names. Second, `evidence` joins the `Report` JSON fields, together with `Evidence`'s
fields (`subject`, `scope`, `offset`, `value`, `basis`) and the basis vocabulary:
`dictionary`, `ambiguous` and `estimated`. `metrics` keys, message wording and hint
wording stay unstable. Tests hold the README to this: every field `Report` serialises,
every `Evidence` field and every basis value must be named in the promise, and the
unstable list must not name rules. `tests/data/published-rules.json` records every row's
published rules, and a test fails when one of them is no longer in `rules(pid)`, telling
whoever removed it to name the removal as breaking and update the snapshot. Additions
pass, so the snapshot only grows by hand.

## Consequences

The parameter shape is a breaking change. Every caller of `multiple_constraint` has to
rewrite its call, including the golden fixtures, the explorer's form and anyone's saved
prompts. The refusal names the new shape, but it still refuses. The CLI's `--param`
now reads a value as JSON when the field's schema type is an array or an object, so
`source='[1]'` is still a one-line source text. On such a field a value that is
well-formed JSON now arrives parsed where it used to arrive as a string; a value of
the wrong shape is refused with `InvalidParams`, never misread.

The mean inherits each constraint's own scale. A row that scores leniently and a row
that scores strictly count the same in it, so the mean says how far each constraint is
from passing as that constraint measures it, not that the two distances are
comparable. A product would punish a composite more steeply for one bad constraint. The
mean was chosen because it moves the least for the case that matters most, one
constraint nearly met, and because it keeps ADR 0005's reading of the score as a
distance. Three golden scores rise (0.5 to 0.667, 0.6875 and 0.667). No verdict moves.

Position-keyed metrics are the price of not changing `Report`'s schema. A reader has to
zip `delegates.<i>.*` with the call's own `constraints` to know which is which. Those
keys sit under `metrics` and so are not promised either.

Promising rule names freezes a vocabulary that has been renamed before. ADR 0056
retired `wrong_word_count` on two rows. Every such cleanup is now a breaking change
with a changelog line, and a rule that turns out to mean two things has to be split by
adding a new rule beside it, not by renaming the old one. The vocabulary is large, and
some rules are worded for the first row that had them rather than for every row that
has them since. That wording is now fixed. `rule_categories` and `failure_categories`
stay unpromised: which category a rule belongs to is still being learned (ADR 0056
moved `missing_letter` on three rows).

Promising `evidence` means a new basis is a schema change, not a quiet addition. It
moves `provenance.schema_version`, as `ambiguous` moved it to 1.2. `Evidence` cannot
gain a confidence number later without that being a new field beside `basis`. Its
docstring already explains why the field has none.
