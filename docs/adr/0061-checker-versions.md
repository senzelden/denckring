# 61. Checker versions

## Context

The package version says a release happened, not which rows' verdicts it moved. The
bench audited 0.3.1 to 0.4.0 by hand, reading the changelog and re-running rows to learn
which of its stored results were still valid. A caller comparing a result stored under
one release with a check under another has only the whole-package version to go on, so it
must either distrust everything or read prose.

## Decision

**B1: every row has a `checker_version`.** `BaseProcedure.checker_version` is a class
attribute, 1 by default, published as `Description.checker_version`. It is bumped by any
change that can move `satisfied`, `score` or the set of violation rules on some text,
which is what a caller scores on. Evidence and message wording do not bump it. Every row
starts at 1 in the release that introduces the field (0.5.0); the earlier moves stay in
the changelog and are not backfilled.

**`Report.provenance.checkers`** maps each row that decided the verdict to its version.
For most rows that is the row itself. A `multiple_constraint` call also names each row it
composes, once, however many times an entry repeats it. `Provenance.schema_version` is
`1.3`. A `Production` carries the same field for its generator's row.

**B2: a shipped history.** `eval/checker-history.yaml` lists, per row and oldest first,
`{version, since, reason}`, `since` being the release the change ships in.
`denckring.checker_history(procedure_id)` returns it as `CheckerChange` entries and
raises `UnknownProcedure` for an id that is not registered. A guard holds each list to
versions `1..n` with `n` equal to the class attribute.

**B3 (a later task): a verdict fingerprint** fails a change that moves a verdict without
a bump.

## Consequences

Every verdict-moving change now needs a bump, a history line and a snapshot refresh. That
is the point and the cost: a fix that moves one score on one text is a three-file change.

A composite's own version does not move when an entry's does, because the composite's
code did not change. That is why `checkers` lists every row, rather than leaving a
caller to infer it from the composite's version.

The version is an integer that says "something moved", not what. The reason in the
history is prose and unenforced beyond being present. The criterion is judgment: the
fingerprint catches a moved verdict on the golden texts, and a verdict that moves only on
a text no golden case covers can still ship without a bump.

`since: "0.5.0"` is the release this is planned to ship in. If it ships under another
number, the baseline entries must be edited with it.
