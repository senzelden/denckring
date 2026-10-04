"""Each row's `violation.rule` vocabulary is declared, complete and reachable.

`BaseProcedure.rules` is what `denckring.rules` publishes, so a consumer can map
rules to its own classes without scanning checker source (audit B1). Two
directions hold it honest. Undeclared: every rule a report carries, across the
golden corpus here and across every unit test through `conftest.declared_rules_only`,
must be in its row's list. Unreached: every declared rule must be emitted by a
golden case or by a witness in `tests/fixtures/rule_witnesses.yaml`, so the list
cannot grow a rule no call can produce: `iambic_pentameter` reaching
`form_report`, which has rhyme rules, does not make it a rhyme checker.
"""

from __future__ import annotations

import ast
import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

import denckring
from denckring.core.errors import DenckringError, UnknownProcedure
from denckring.core.registry import all_procedures, get
from denckring.eval.harness import golden_cases, unmet_requirements
from denckring.lang import get_pack

WITNESSES = Path(__file__).parent / "fixtures" / "rule_witnesses.yaml"
RULE_ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


def _witnesses() -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = yaml.safe_load(WITNESSES.read_text(encoding="utf-8"))["witnesses"]
    return data


def _golden_emitted() -> set[tuple[str, str]]:
    emitted: set[tuple[str, str]] = set()
    for case in golden_cases():
        if unmet_requirements(case, get_pack(case.lang)):
            continue
        try:
            report = get(case.procedure).check(case.text, lang=case.lang, **case.params)
        except DenckringError:
            continue
        emitted |= {(case.procedure, violation.rule) for violation in report.violations}
    return emitted


@pytest.fixture(scope="module")
def golden_emitted() -> set[tuple[str, str]]:
    return _golden_emitted()


def _declares_rules_itself(cls: type) -> bool:
    """Whether `rules` is assigned in the class's own body, not inherited."""
    tree = ast.parse(inspect.getsource(cls))
    body = tree.body[0]
    assert isinstance(body, ast.ClassDef)
    return any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "rules" for target in node.targets)
        for node in body.body
    )


def test_every_row_declares_its_rules_in_its_own_class_body() -> None:
    """Inheriting a parent's list would publish the parent's vocabulary silently."""
    missing = [
        pid
        for pid, procedure in all_procedures().items()
        if not _declares_rules_itself(type(procedure))
    ]
    assert missing == []


def test_declared_rules_are_sorted_unique_ids() -> None:
    malformed = {
        pid: procedure.rules
        for pid, procedure in all_procedures().items()
        if list(procedure.rules) != sorted(set(procedure.rules))
        or not all(RULE_ID.fullmatch(rule) for rule in procedure.rules)
    }
    assert malformed == {}


def test_only_a_delegating_row_declares_no_rules() -> None:
    empty = sorted(pid for pid, procedure in all_procedures().items() if not procedure.rules)
    delegating = sorted(
        pid for pid, procedure in all_procedures().items() if procedure.delegates_rules
    )
    assert empty == delegating == ["multiple_constraint"]


def test_every_rule_the_golden_corpus_emits_is_declared(
    golden_emitted: set[tuple[str, str]],
) -> None:
    undeclared = sorted(
        (pid, rule) for pid, rule in golden_emitted if rule not in denckring.rules(pid)
    )
    assert undeclared == []


def test_every_declared_rule_is_emitted_by_a_golden_case_or_a_witness(
    golden_emitted: set[tuple[str, str]],
) -> None:
    witnessed = {(entry["procedure"], entry["rule"]) for entry in _witnesses()}
    unreached = sorted(
        (pid, rule)
        for pid, procedure in all_procedures().items()
        for rule in procedure.rules
        if (pid, rule) not in golden_emitted | witnessed
    )
    assert unreached == []


@pytest.mark.parametrize(
    "entry", _witnesses(), ids=lambda entry: f"{entry['procedure']}:{entry['rule']}"
)
def test_each_witness_emits_its_rule(entry: dict[str, Any]) -> None:
    report = get(entry["procedure"]).check(entry["text"], lang=entry["lang"], **entry["params"])
    assert entry["rule"] in {violation.rule for violation in report.violations}
    assert entry["rule"] in denckring.rules(entry["procedure"])


def test_no_witness_duplicates_a_golden_case(golden_emitted: set[tuple[str, str]]) -> None:
    """A rule the corpus already emits needs no witness; a stale one only hides drift."""
    entries = [(entry["procedure"], entry["rule"]) for entry in _witnesses()]
    assert len(entries) == len(set(entries))
    assert sorted(set(entries) & golden_emitted) == []


def test_rules_reads_the_declaration() -> None:
    assert denckring.rules("lipogram") == ("forbidden_letter",)
    assert denckring.rules("iambic_pentameter") == ("wrong_line_length", "wrong_stress")


def test_a_composite_answers_with_every_other_rows_vocabulary() -> None:
    union = {
        rule
        for pid, procedure in all_procedures().items()
        if pid != "multiple_constraint"
        for rule in procedure.rules
    }
    assert denckring.rules("multiple_constraint") == tuple(sorted(union))


def test_a_composite_passes_its_constraints_rules_through() -> None:
    report = denckring.check(
        "multiple_constraint",
        "the cat",
        constraints=[{"id": "lipogram", "params": {"forbidden": "t"}}, {"id": "univocalic"}],
    )
    rules = {violation.rule for violation in report.violations}
    assert "forbidden_letter" in rules
    assert rules <= set(denckring.rules("multiple_constraint"))


def test_rules_refuses_an_unknown_row() -> None:
    with pytest.raises(UnknownProcedure):
        denckring.rules("no_such_row")


def test_every_row_taking_unknown_rhyme_can_fail_on_it() -> None:
    """A row that accepts `unknown_rhyme` and never reads it ignores a caller's `strict`.

    Seventeen rows did until 0.3.2. Declaring the rule here, with the reach test above
    demanding a golden case or witness for it, proves `strict` takes effect.
    """
    ignoring = sorted(
        pid
        for pid, procedure in all_procedures().items()
        if "unknown_rhyme" in procedure.params_model().model_fields
        and "unknown_rhyme" not in procedure.rules
    )
    assert ignoring == []


def test_a_row_without_rules_is_named_even_through_the_composite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forgotten declaration names the row at fault, not `multiple_constraint`."""
    monkeypatch.delattr(type(get("lipogram")), "rules")
    with pytest.raises(TypeError, match="'lipogram' declares no `rules`"):
        denckring.rules("multiple_constraint")
    with pytest.raises(TypeError, match="'lipogram' declares no `rules`"):
        denckring.rules("lipogram")


#: Every published rule, per row, as of the release that promised them (ADR 0059).
PUBLISHED = Path(__file__).parent / "data" / "published-rules.json"


def test_no_published_rule_is_removed_or_renamed() -> None:
    """The README promises that a rule `denckring.rules` publishes keeps its name and
    meaning (ADR 0059). A row may add rules, so only a snapshot rule that has gone
    fails; a new one needs no change here, though adding it keeps the guard current."""
    snapshot: dict[str, list[str]] = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    rows = all_procedures()
    gone = {
        pid: sorted(set(published) - set(denckring.rules(pid) if pid in rows else ()))
        for pid, published in snapshot.items()
    }
    gone = {pid: missing for pid, missing in gone.items() if missing}
    assert not gone, (
        f"published rules removed or renamed: {gone}. That is a breaking change: name it "
        f"under **Breaking:** in CHANGELOG.md, then update {PUBLISHED.name}"
    )
