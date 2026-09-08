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
import re
from pathlib import Path

from conftest import load_golden_cases
from denckring import check

#: Matches a `rule="..."` or `rule='...'` literal, the shape every checker uses to
#: construct a Violation. Scanning the source for these rather than copying them
#: into a second list here means a rule added tomorrow is recognised tomorrow.
_RULE_LITERAL = re.compile(r"""rule\s*=\s*["']([a-z_]+)["']""")

#: A `source` field's backtick spans include things that are not rule names —
#: Middle English words, ADR numbers, stress patterns like `101` — so a claimed
#: rule only counts if it is one the codebase actually defines.
_BACKTICKED = re.compile(r"`([^`]+)`")

_SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "denckring"

#: The measurement above, as a floor rather than a pin. A guard that fixes the
#: current answer fails on the change that is correct — adding a sourced case is
#: exactly the improvement this file exists to encourage — so it asserts the
#: number does not fall, not that it stays. Raised from 38 to 51 when ADR 0040's
#: canonical corpus landed.
EXTERNAL_FLOOR = 51


def test_every_case_says_where_it_came_from() -> None:
    """A case with no source cannot be audited by anyone, including its author a
    year later. All 532 have one today; this is what keeps the next one honest."""
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
    was plausible read alone and false on inspection. This runs every such case and
    checks its claim against what the checker actually says, so a false explanation
    fails the suite instead of sitting in the corpus looking read."""
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
