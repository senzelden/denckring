"""Fixtures shared by the three registry-wide suites."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

import denckring
from denckring.core.base import BaseProcedure
from denckring.core.protocol import Lang, Report
from denckring.core.registry import all_procedures

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "src/denckring/eval/fixtures/golden"
STRATEGY_DIR = Path(__file__).resolve().parent / "strategies"


@dataclass(frozen=True)
class GoldenCase:
    procedure: str
    lang: Lang
    name: str
    text: str
    params: dict[str, Any]
    satisfied: bool
    #: Loaded rather than dropped. This field was absent here while every one of
    #: the 122 fixture files carried it, so provenance was decorative — written
    #: down, read by nobody, and asserted on by nothing.
    source: str | None
    provenance: str
    min_score: float | None
    max_score: float | None

    def __str__(self) -> str:
        return f"{self.procedure}:{self.lang}:{self.name}"


def load_golden_cases() -> list[GoldenCase]:
    cases: list[GoldenCase] = []
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        default_lang = data.get("lang", "en")
        for case in data["cases"]:
            cases.append(
                GoldenCase(
                    procedure=data["procedure"],
                    lang=case.get("lang", default_lang),
                    name=case["name"],
                    text=case["text"],
                    params=case.get("params", {}),
                    satisfied=case["satisfied"],
                    source=case.get("source"),
                    provenance=case.get("provenance", "constructed"),
                    min_score=case.get("min_score"),
                    max_score=case.get("max_score"),
                )
            )
    return cases


def strategy_module(procedure_id: str) -> ModuleType:
    return importlib.import_module(f"strategies.{procedure_id}")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "procedure_id" in metafunc.fixturenames:
        ids = sorted(all_procedures())
        metafunc.parametrize("procedure_id", ids, ids=ids)
    if "golden_case" in metafunc.fixturenames:
        cases = load_golden_cases()
        metafunc.parametrize("golden_case", cases, ids=[str(c) for c in cases])


@pytest.fixture(autouse=True)
def declared_rules_only(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail any test whose reports carry a `violation.rule` its row does not declare.

    Every `check` call in the suite goes through here, so the unit tests, and not
    only the golden corpus, hold each row to its published vocabulary
    (`BaseProcedure.rules`). Asserted at teardown rather than raised from inside
    `check`, so a test expecting an exception cannot swallow it. A procedure the
    test built itself and never registered has no published vocabulary, and is
    skipped.
    """
    emitted: list[tuple[str, str]] = []
    original = BaseProcedure.check

    def recording(self: BaseProcedure[Any], text: str, **kwargs: Any) -> Report:
        report = original(self, text, **kwargs)
        if all_procedures().get(self.id) is self:
            emitted.extend((self.id, violation.rule) for violation in report.violations)
        return report

    monkeypatch.setattr(BaseProcedure, "check", recording)
    yield
    undeclared = sorted({(pid, rule) for pid, rule in emitted if rule not in denckring.rules(pid)})
    assert not undeclared, f"rules emitted but not declared in `rules`: {undeclared}"
