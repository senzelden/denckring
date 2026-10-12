"""The surfaces denckring-bench reads, held to the promise the README makes (ADR 0060)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import denckring
from denckring.core.fields import ROLE_KEY
from denckring.eval.harness import evidence_gaps

PUBLISHED_ROLES = Path(__file__).parent / "data" / "published-roles.json"


def test_unmet_requirements_is_exported() -> None:
    assert "unmet_requirements" in denckring.__all__
    case = denckring.GoldenCase(
        procedure="lipogram", name="x", text="x", satisfied=True, requires=["no.such.cap"]
    )
    assert denckring.unmet_requirements(case, denckring.get_pack("en")) == ["no.such.cap"]


def test_parameter_roles_are_exported_read_only() -> None:
    assert "PARAMETER_ROLES" in denckring.__all__
    with pytest.raises(TypeError):
        denckring.PARAMETER_ROLES["new"] = "x"  # type: ignore[index]


def test_every_role_a_schema_names_is_published() -> None:
    """A role in a schema that `PARAMETER_ROLES` does not define would be a word the
    bench cannot look up."""
    named = {
        spec[ROLE_KEY]
        for pid in denckring.all_procedures()
        for spec in denckring.describe(pid).params.get("properties", {}).values()
        if ROLE_KEY in spec
    }
    assert named <= set(denckring.PARAMETER_ROLES)


def test_no_published_role_is_removed() -> None:
    """Adding a role is allowed; removing or renaming one breaks the promise."""
    snapshot: list[str] = json.loads(PUBLISHED_ROLES.read_text(encoding="utf-8"))
    gone = sorted(set(snapshot) - set(denckring.PARAMETER_ROLES))
    assert not gone, f"published roles removed: {gone}; name it under **Breaking:**"


PUBLISHED_METRICS = Path(__file__).parent / "data" / "published-metrics.json"


def test_chronogram_promises_its_total() -> None:
    assert {"total", "numerals"} <= set(denckring.describe("chronogram").metrics)


def test_every_promised_metric_is_in_every_golden_report() -> None:
    """A promise the checker does not keep is worse than none (ADR 0060 D3)."""
    missing = []
    for case in denckring.golden_cases():
        promised = denckring.describe(case.procedure).metrics
        if not promised:
            continue
        report = denckring.check(case.procedure, case.text, lang=case.lang, **case.params)
        for key in promised:
            if not isinstance(report.metrics.get(key), float):
                missing.append(f"{case.procedure}/{case.name}: {key}")
    assert not missing, missing


def test_no_promised_metric_is_removed() -> None:
    snapshot: dict[str, list[str]] = json.loads(PUBLISHED_METRICS.read_text(encoding="utf-8"))
    gone = {
        pid: sorted(set(keys) - set(denckring.describe(pid).metrics))
        for pid, keys in snapshot.items()
    }
    gone = {pid: keys for pid, keys in gone.items() if keys}
    assert not gone, f"promised metrics removed: {gone}; name it under **Breaking:**"


def test_corpus_share_is_exported_and_described() -> None:
    """ADR 0062: the per-row share a caller weighs a row's verdicts by."""
    assert "CorpusShare" in denckring.__all__
    assert isinstance(denckring.describe("acrostic").corpus, denckring.CorpusShare)


def test_describe_corpus_counts_the_rows_golden_cases() -> None:
    """Counted over the whole corpus (`runnable=False`), by provenance and recorded
    verdict, so the share does not depend on which packs this install has."""
    for pid in ("acrostic", "n_plus_7", "chronogram"):
        cases = denckring.golden_cases(runnable=False)
        mine = [c for c in cases if c.procedure == pid]
        corpus = denckring.describe(pid).corpus
        assert corpus.external_passing == sum(
            c.provenance == "external" and c.satisfied for c in mine
        )
        assert corpus.external_failing == sum(
            c.provenance == "external" and not c.satisfied for c in mine
        )
        assert corpus.constructed == sum(c.provenance == "constructed" for c in mine)
        assert corpus.self_generated == sum(c.provenance == "self-generated" for c in mine)


def test_corpus_gap_is_the_registry_reason() -> None:
    """`describe` publishes the registry's reason for every row, and `None` for a row
    the registry does not list, whatever the reason or row (ADR 0062)."""
    gaps = evidence_gaps()
    wrong = {
        pid: (denckring.describe(pid).corpus.gap, gaps[pid].reason if pid in gaps else None)
        for pid in denckring.all_procedures()
        if denckring.describe(pid).corpus.gap != (gaps[pid].reason if pid in gaps else None)
    }
    assert not wrong, f"describe's gap differs from the registry (described, registry): {wrong}"
