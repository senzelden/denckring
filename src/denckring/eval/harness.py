"""Level 3: the scoreboard. This is the CI gate and the unattended-run criterion."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from denckring.core import catalogue
from denckring.core.errors import DenckringError
from denckring.core.protocol import Lang
from denckring.core.registry import all_procedures, get

GOLDEN_DIR = Path(str(files("denckring") / "eval" / "fixtures" / "golden"))


class GoldenCase(BaseModel):
    """One recorded example, positive or negative, for a procedure."""

    procedure: str
    lang: Lang = "en"
    name: str
    text: str
    params: dict[str, Any] = Field(default_factory=dict)
    satisfied: bool
    source: str | None = None
    min_score: float | None = None
    max_score: float | None = None


class CaseResult(BaseModel):
    case: str
    procedure: str
    lang: Lang
    passed: bool
    detail: str | None = None
    #: The `DenckringError.code` of the refusal, where the case failed by
    #: raising rather than by disagreeing. `detail` has always carried the
    #: message and threw away the one machine-readable field the error has, so
    #: a consumer wanting to tell "this install lacks the data" from "this
    #: checker is wrong" had to match English prose for it.
    code: str | None = None


class Coverage(BaseModel):
    """The project metric.

    `implementable` excludes rows that can never have a checker, so the gap
    between it and `implemented` describes work that can actually be done.

    Every field but `instruments` counts the `verfahren` layer alone (ADR 0033 D3).
    Folding both layers into one total would make `155 catalogued` mean something
    different from what it meant in every ADR that recorded it, and the 500 target is
    a target for `verfahren` (D4), so the instrument count is reported beside these
    numbers rather than inside them.
    """

    catalogued: int
    implementable: int
    implemented: int
    validated: int
    unreachable: int
    #: Reads 0 until the first instrument entry lands, which is the expected state
    #: after ADR 0033 rather than an unfinished migration.
    instruments: int

    def line(self) -> str:
        return (
            f"{self.catalogued} catalogued · "
            f"{self.implementable} implementable · "
            f"{self.implemented} implemented · "
            f"{self.validated} validated · "
            f"{self.unreachable} not mechanically checkable"
        )

    def instrument_line(self) -> str:
        """The second counter, on a line of its own so the first keeps its meaning."""
        return f"{self.instruments} instruments catalogued"


class Scoreboard(BaseModel):
    results: list[CaseResult]
    coverage: Coverage

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def golden_cases() -> list[GoldenCase]:
    """Every shipped golden example, across every procedure."""
    cases: list[GoldenCase] = []
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        default_lang = data.get("lang", "en")
        for row in data["cases"]:
            # A case may override the file's language, so English and German
            # examples of the same procedure live in one file.
            cases.append(GoldenCase(procedure=data["procedure"], **{"lang": default_lang, **row}))
    return cases


def implemented_ids() -> list[str]:
    """Every `verfahren` procedure that has a registered module.

    Intersected with the catalogue rather than read straight off the registry, so
    that an instrument shipping a checker of its own could not move the five-part
    line by the back door. `tests/test_registry.py` holds registered ids to a subset
    of the catalogue, so nothing else is lost in the intersection.
    """
    return sorted(set(all_procedures()) & set(catalogue.ids("verfahren")))


def validated_ids() -> list[str]:
    """Every implemented procedure that also has golden examples."""
    with_fixtures = {c.procedure for c in golden_cases()}
    return sorted(with_fixtures & set(implemented_ids()))


def implementable_ids() -> list[str]:
    """`verfahren` rows that could have a checker, whether or not they do."""
    return sorted(
        pid for pid in catalogue.ids("verfahren") if catalogue.get(pid).checkability != "none"
    )


def status() -> Coverage:
    """Count the catalogue against what is implementable, implemented and validated."""
    catalogued = catalogue.ids("verfahren")
    implementable = implementable_ids()
    return Coverage(
        catalogued=len(catalogued),
        implementable=len(implementable),
        implemented=len(implemented_ids()),
        validated=len(validated_ids()),
        unreachable=len(catalogued) - len(implementable),
        instruments=len(catalogue.ids("instrument")),
    )


def run() -> Scoreboard:
    """Run every golden case through its procedure."""
    results: list[CaseResult] = []
    for case in golden_cases():
        detail: str | None = None
        code: str | None = None
        try:
            report = get(case.procedure).check(case.text, lang=case.lang, **case.params)
            passed = report.satisfied is case.satisfied
            if passed and case.min_score is not None:
                passed = report.score >= case.min_score
            if passed and case.max_score is not None:
                passed = report.score <= case.max_score
            if not passed:
                detail = f"satisfied={report.satisfied} score={report.score:.3f}"
        except DenckringError as exc:
            passed = False
            detail = str(exc)
            code = exc.code
        results.append(
            CaseResult(
                case=case.name,
                procedure=case.procedure,
                lang=case.lang,
                passed=passed,
                detail=detail,
                code=code,
            )
        )
    return Scoreboard(results=results, coverage=status())
