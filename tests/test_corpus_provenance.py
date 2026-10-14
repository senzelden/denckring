"""Where the golden cases came from, asserted rather than merely written down.

`denckring eval --all` reports 532 passing cases, and until this file existed
that number said nothing about whether the checkers read their constraints
correctly. An implementation and its own examples agree by construction: both
come from one author on one afternoon, and a misreading of a form is present in
both or neither. A green suite cannot tell you which.

The measurement this file makes assertable, taken on 2026-09-07: **38 of 532
cases (7.1%) name a source outside this repository.** 491 were written for the
suite, and 3 were produced by the implementation they test.

None of that is a defect on its own — a counterexample nearly always has to be
built, because published sources record the forms that succeed and rarely the
near-misses a checker most needs to reject. What was a defect is that the ratio
was invisible: `source` was carried in all 122 fixture files and dropped by the
loader, so nothing could report it and nothing could stop it falling.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path

from conftest import load_golden_cases
from denckring import check
from denckring.eval.harness import evidence_gaps, implemented_rows

#: Matches a `rule="..."` or `rule='...'` literal, the shape every checker uses to
#: construct a Violation. Scanning the source for these rather than copying them
#: into a second list here means a rule added tomorrow is recognised tomorrow.
_RULE_LITERAL = re.compile(r"""rule\s*=\s*["']([a-z_]+)["']""")

#: A `source` field's backtick spans include things that are not rule names —
#: Middle English words, ADR numbers, stress patterns like `101` — so a claimed
#: rule only counts if it is one the codebase actually defines.
_BACKTICKED = re.compile(r"`([^`]+)`")

#: A `source` that states "Measured on this HEAD: score 0.9873" is making a claim
#: that can go stale the moment a dependency's data changes underneath it (ADR
#: 0040 records exactly that for `denckring-de-data`). Matching the phrase, not
#: one instance of it, so a case that starts stating a score is caught whether
#: or not it is one of today's eight.
_STATES_A_MEASURED_SCORE = re.compile(r"score\s+\d\.\d+")

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "denckring"

#: The measurement above, as a floor rather than a pin. A guard that fixes the
#: current answer fails on the change that is correct — adding a sourced case is
#: exactly the improvement this file exists to encourage — so it asserts the
#: number does not fall, not that it stays. Raised from 38 to 51 when ADR 0040's
#: canonical corpus landed, and from 66 to 85 when ADR 0062 added the per-row ratchet
#: below: the floor had trailed the corpus by nineteen cases, so it could have fallen
#: that far without a failure. Raised to 98 later on 2026-10-12, when the public-domain
#: sourcing pass for the classical verse forms landed thirteen cases, and to 102 when four
#: of Hilton's chronograms (1882) landed. Raised to 118 on 2026-10-13, when Bombaugh's 1890
#: chronogram and fifteen cases from his telestich, acrostic, double acrostic, univocalic
#: and lipogram texts landed. Raised to 119 on 2026-10-14, when Lear's "Ryde" limerick
#: landed with the identical-rhyme fix it witnesses, and to 120 when a Don Juan stanza
#: landed with `ottava_rima`'s new feminine_ending. Raised to 124 when four ballades from
#: Gleeson White's anthology (1887) landed with `ballade`'s new `metre`, and to 125 when
#: the anonymous s-less song quoted in The Galaxy (1866) landed for `consonantal_lipogram`.
EXTERNAL_FLOOR = 125

#: The same floor as a share of the corpus (ADR 0062), so that adding constructed cases
#: faster than external ones shows up. 85 of 687 on 2026-10-12, rounded down to three
#: places so the measured value itself passes; raised with the floor above, at 98 of 700
#: (0.140), and at 102 of 704 (0.144). Lowered once, deliberately, to 102 of 722 (0.141):
#: ADR 0063 declares German on twenty letter rules and every one of the eighteen German
#: cases it needed is constructed. The fall is the cost that ADR records, not drift.
#: Raised to 118 of 739 (0.159) when the Bombaugh 1890 cases landed, above the 0.144 the
#: dip had given up. Raised to 119 of 740 (0.160) with Lear's "Ryde" limerick, and to
#: 120 of 741 (0.161) with the Don Juan stanza, and to 124 of 745 (0.166) with White's
#: four ballades, and to 125 of 746 (0.167) with the Galaxy's s-less song.
EXTERNAL_SHARE_FLOOR = 0.167

#: Per-row external counts, a ratchet: a row may gain external cases, never lose one
#: (ADR 0062). Rewritten by hand when a row gains one, in the same commit.
EXTERNAL_FLOOR_FILE = Path(__file__).parent / "data" / "external-floor.json"


def test_every_case_says_where_it_came_from() -> None:
    """A case with no source cannot be audited by anyone, including its author a
    year later. Every case must name one, so a new case cannot land without a source."""
    unsourced = [str(case) for case in load_golden_cases() if not (case.source or "").strip()]
    assert not unsourced, f"{len(unsourced)} golden cases name no source: {unsourced[:5]}"


def test_the_externally_sourced_corpus_does_not_shrink() -> None:
    """The one number that is evidence about the *reading* of a constraint rather
    than about the code, so it is the one worth defending."""
    counts = collections.Counter(case.provenance for case in load_golden_cases())
    assert counts["external"] >= EXTERNAL_FLOOR, (
        f"externally sourced cases fell to {counts['external']} from {EXTERNAL_FLOOR}; "
        f"raising this corpus is the point, lowering it is a regression"
    )


def test_provenance_is_one_of_the_three_values() -> None:
    """The loader defaults an unmarked case to `constructed`, so a typo in the
    YAML would otherwise be silently read as the conservative value and count
    against nothing."""
    allowed = {"external", "constructed", "self-generated"}
    wrong = {case.provenance for case in load_golden_cases()} - allowed
    assert not wrong, f"unknown provenance values in the fixtures: {sorted(wrong)}"


def test_a_self_generated_case_is_never_the_only_evidence() -> None:
    """A case the implementation produced and its own checker accepted tests the
    round trip and cannot test the reading — a generator and a checker sharing a
    misunderstanding agree perfectly. Such a row needs at least one case that did
    not come out of itself."""
    by_procedure: dict[str, set[str]] = collections.defaultdict(set)
    for case in load_golden_cases():
        by_procedure[case.procedure].add(case.provenance)
    alone = sorted(p for p, kinds in by_procedure.items() if kinds == {"self-generated"})
    assert not alone, f"{alone} are evidenced only by their own output"


def _known_rule_names() -> set[str]:
    names: set[str] = set()
    for path in _SRC_ROOT.rglob("*.py"):
        names.update(_RULE_LITERAL.findall(path.read_text(encoding="utf-8")))
    return names


def _rules_claimed(source: str, known_rules: set[str]) -> set[str]:
    return {token for token in _BACKTICKED.findall(source) if token in known_rules}


def test_an_external_rejection_names_a_rule_the_checker_actually_raised() -> None:
    """A `satisfied: false` external case earns its place by explaining what this
    package makes of a published text — that is its whole value, since `eval --all`
    only checks that `satisfied` matches and cannot check that the explanation is
    true. Three cases shipped with a `source` naming a rule the checker never raised
    for them: one blamed `wrong_stress` on a line the row does not scan stress for
    at all, two blamed a missing dictionary entry on a word the dictionary held. Each
    was plausible read alone and false on inspection. This catches only the first
    kind: a backticked token that is a recognised rule name, checked against what the
    checker actually raised for that case. The other two above were prose ("a word
    not in this package's phonetic database") and would pass this guard untouched —
    prose claims and line attributions in `source` remain unguarded."""
    known_rules = _known_rule_names()
    unbacked = []
    for case in load_golden_cases():
        if case.provenance != "external" or case.satisfied:
            continue
        claimed = _rules_claimed(case.source or "", known_rules)
        if not claimed:
            continue
        report = check(case.procedure, case.text, lang=case.lang, **case.params)
        emitted = {v.rule for v in report.violations}
        for rule in sorted(claimed - emitted):
            unbacked.append(
                f"{case}: source names `{rule}`, but the checker raised {sorted(emitted)}"
            )
    assert not unbacked, "\n".join(unbacked)


def test_a_stated_score_is_backed_by_a_min_score_floor() -> None:
    """`eval --all` only checks `satisfied`, not `score` — a `satisfied: false` case
    passes no matter what its `params` say, which is how one shipped missing
    `feminine_ending: true` and stayed green. A `source` that states a measured
    score (`Measured on this HEAD: score 0.9873`) is a claim about that score, and
    without a `min_score` floor nothing in the suite would notice if a later change
    moved it. The rule, not today's count: any external, unsatisfied case whose
    `source` states a measured score must carry a `min_score`."""
    unbacked = [
        str(case)
        for case in load_golden_cases()
        if case.provenance == "external"
        and not case.satisfied
        and _STATES_A_MEASURED_SCORE.search(case.source or "")
        and case.min_score is None
    ]
    assert not unbacked, f"cases state a measured score with no min_score to guard it: {unbacked}"


def _external_rows() -> set[str]:
    return {c.procedure for c in load_golden_cases() if c.provenance == "external"}


def test_every_implemented_row_is_evidenced_or_explained() -> None:
    """ADR 0062: a row with no published text behind its reading says why, so the gap
    is a recorded fact rather than an unnoticed one."""
    gaps = evidence_gaps()
    unexplained = sorted(implemented_rows() - _external_rows() - set(gaps))
    assert not unexplained, f"rows with no external case and no gap entry: {unexplained}"


def test_no_gap_entry_outlives_its_gap() -> None:
    stale = sorted(set(evidence_gaps()) & _external_rows())
    assert not stale, f"rows now externally evidenced; remove their gap entries: {stale}"


def test_gap_entries_name_implemented_rows() -> None:
    """An entry for a misspelt id, or for a catalogued row with no checker, explains a
    gap nobody can have."""
    unknown = sorted(set(evidence_gaps()) - implemented_rows())
    assert not unknown, unknown


def test_none_found_names_what_was_searched() -> None:
    bare = [
        row
        for row, gap in evidence_gaps().items()
        if gap.reason == "none_found" and not gap.note.strip()
    ]
    assert not bare, bare


def test_no_row_loses_external_evidence() -> None:
    floor: dict[str, int] = json.loads(EXTERNAL_FLOOR_FILE.read_text(encoding="utf-8"))
    counts = collections.Counter(
        c.procedure for c in load_golden_cases() if c.provenance == "external"
    )
    fell = {r: (counts[r], n) for r, n in floor.items() if counts[r] < n}
    assert not fell, f"external cases fell (now, floor): {fell}"


def test_the_external_share_does_not_fall() -> None:
    cases = load_golden_cases()
    share = sum(c.provenance == "external" for c in cases) / len(cases)
    assert share >= EXTERNAL_SHARE_FLOOR, f"external share {share:.3f} < {EXTERNAL_SHARE_FLOOR}"
