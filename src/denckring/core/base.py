"""The template method every procedure inherits.

`check` validates language, capability and parameters before delegating, so an
individual procedure module cannot forget those checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from denckring.core import catalogue
from denckring.core.errors import InvalidParams, MissingCapability
from denckring.core.protocol import Lang, LanguagePack, Meta, Report, Violation

P = TypeVar("P", bound=BaseModel)


class BaseProcedure(ABC, Generic[P]):
    """A procedure. Subclasses live one per module and are registered by decorator."""

    id: ClassVar[str]

    def __init__(self) -> None:
        self.meta: Meta = catalogue.get(self.id)

    @classmethod
    @abstractmethod
    def params_model(cls) -> type[P]:
        """The Pydantic model describing this procedure's parameters."""

    @abstractmethod
    def _check(self, text: str, pack: LanguagePack, params: P) -> Report:
        """Procedure-specific checking. Language and parameters are already valid."""

    def params_schema(self) -> dict[str, Any]:
        """JSON Schema for the parameters, for non-Python callers."""
        return self.params_model().model_json_schema()

    def check(self, text: str, *, lang: Lang = "en", **params: Any) -> Report:
        """Validate a text against this procedure."""
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in self.meta.requires:
            require_capability(pack, capability, self.id)
        try:
            parsed = self.params_model().model_validate(params)
        except ValidationError as exc:
            raise InvalidParams(self.id, str(exc)) from exc
        return self._check(text, pack, parsed)

    def _report(
        self,
        *,
        good: int,
        total: int,
        violations: list[Violation],
        metrics: dict[str, float],
    ) -> Report:
        """Build a Report enforcing `satisfied == (score == 1.0)`.

        An empty text has `total == 0` and scores 1.0 — vacuously satisfied. A
        procedure for which that is wrong (pangram) must not use this helper.
        """
        score = 1.0 if total == 0 else max(0.0, min(1.0, good / total))
        return Report(
            procedure=self.id,
            satisfied=score == 1.0,
            score=score,
            violations=violations,
            metrics=metrics,
        )


def require_capability(pack: LanguagePack, capability: str, procedure_id: str) -> None:
    """Raise `MissingCapability` unless the pack declares it."""
    if capability not in pack.capabilities:
        raise MissingCapability(procedure_id, pack.lang, capability)
