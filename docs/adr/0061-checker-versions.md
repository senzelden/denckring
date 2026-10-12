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
For most rows that is the row itself. A delegating row also names each row it delegates
to, and a `multiple_constraint` call each row it composes, once, however many times an
entry repeats it. The closure is transitive: an entry naming `telestich` brings
`acrostic` too, since an `acrostic` bump moves that verdict while neither the
composite's version nor `telestich`'s does. `Provenance.schema_version` is
`1.3`. A `Production` carries the same field for its generator's row.

**Delegation is declared, not inferred.** A row that runs another row's checker, or
subclasses it, lists it in `BaseProcedure.composes` (`sestina` runs `quenina`;
`lipogrammatic_translation` and `univocalic_translation` take their verdict from
`lipogram` and `univocalic`; `telestich` inherits `acrostic`). `multiple_constraint`
overrides `_composed_ids` instead, since its delegates depend on the call. A guard scans
the procedure modules for `get("<id>")`, an instantiated row class that is `check`ed, and
registered base classes, and fails a row that omits one.

**B2: a shipped history.** `eval/checker-history.yaml` lists, per row and oldest first,
`{version, since, reason}`, `since` being the release the change ships in.
`denckring.checker_history(procedure_id)` returns it as `CheckerChange` entries and
raises `UnknownProcedure` for an id that is not registered. A guard holds each list to
versions `1..n` with `n` equal to the class attribute.

**B3: a verdict fingerprint** fails a change that moves a verdict without a bump.
`denckring.eval.fingerprint` builds probes per row and language: every distinct golden
text crossed with every distinct parameter set of that row's golden cases in that
language. Per probe, `tests/data/verdict-fingerprints.json` stores two 16-hex digests,
`{"<row>": {"<probe key>": ["<outcome>", "<checkers>"]}}`. The probe key hashes `[lang,
text, params]`. The outcome hashes `satisfied`, the score rounded to six places and the
sorted set of violation rules, or is `error:<code>` for a probe that raises a
`DenckringError`. The checkers digest hashes the sorted items of
`report.provenance.checkers`; for an error, the row's own version and its static
`composes`, closed the same way. For a probe in both snapshot and run, an outcome that
moved under an unchanged checkers digest fails as "verdict moved without a
checker_version bump"; a changed checkers digest fails as "checker_version bumped",
asking for `--write`. A probe added or gone fails as "golden probes changed", never as a
verdict move. `--write` refuses while any unbumped move stands, so the snapshot cannot
launder one.

The digest is per probe rather than one version per row, because a single row version
would make a delegating row (`sestina`, the two translations, `telestich`) bump its own
version whenever only its delegate changed, and cannot express `multiple_constraint`,
whose delegates depend on the call. Hashing `provenance.checkers` makes a `quenina` bump
show on `sestina`'s probes as a bump, which is how it was red-proofed.

**D4: a row that totals letter values publishes how it counts.**
`Description.reading.counting` is a `Counting` (`values`, `combine`, `subtractive`,
`every_occurrence`, `case_sensitive`, `folds`, `skipped`), `None` on a row that counts
nothing. `chronogram` declares it beside `VALUES` and builds the table from it, so the
published values are the ones `_check` sums. The bench had to read the checker to learn
that `IV` totals 6 and that a numeral letter is never passed over; it now reads them.
`tests/test_counting.py` runs each claim against `check`, so a claim that the checker
stops honouring fails. The golden case `chronogram-my-day-closed` now quotes Hilton's
own verdict (*Chronograms*, 1882, p. 9), transcribed from the page image because the
archive.org OCR misreads it, in place of a paraphrase; its text, parameters and verdict
are unchanged, which the verdict fingerprint confirms.

## Consequences

Every verdict-moving change now needs a bump, a history line and a snapshot refresh. That
is the point and the cost: a fix that moves one score on one text is a three-file change.

Helpers shared as plain functions (`form_report`, `pattern_result`, `letter_counts` and
the like) are not rows and are not named: a change to one moves every row that calls it,
and the guard cannot see which. Only a row that defers to another row is declared. The
scan is syntactic, so a delegation through a variable or a helper in `core/` would pass
it unnoticed.

A composite's own version does not move when an entry's does, because the composite's
code did not change. That is why `checkers` lists every row, rather than leaving a
caller to infer it from the composite's version.

The snapshot held 1,098 probes in a file of about 4,700 lines when it was introduced,
and it grows with the corpus; every bump or new golden case rewrites part of it. The
probes are the golden cases' own texts and parameters, so a row with one parameter set
is probed at that set alone.

Probes come from the cases this install can run. On an install missing a data pack, a
row loses probes, and a row that stays runnable can lose parameter sets. So the guard
skips there, and `--write` refuses, naming the cases it cannot run, rather than write a
truncated snapshot. The guard therefore runs only where every pack is installed, which
every CI test job does.

The version is an integer that says "something moved", not what. The reason in the
history is prose and unenforced beyond being present. The criterion is judgment: the
fingerprint catches a moved verdict on the golden texts, and a verdict that moves only on
a text no golden case covers can still ship without a bump.

`since: "0.5.0"` is the release this is planned to ship in. If it ships under another
number, the baseline entries must be edited with it.

`Counting` is a promised shape (README, "What is stable"), so a field removed from it is
**Breaking:**. Only one row declares it; a second counting row must declare its own, and
nothing yet finds one that forgot. The quoted source is retyped from a page image, so it
rests on a reading of the scan rather than on a file a script can compare it against.
