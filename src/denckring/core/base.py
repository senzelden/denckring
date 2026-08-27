"""The template method every procedure inherits.

`check` validates language, capability and parameters before delegating, so an
individual procedure module cannot forget those checks. `ConstructiveProcedure`
gives `apply` the same spine, which it went without because ADR 0002 made it
optional and so kept it off `BaseProcedure` entirely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, Field, ValidationError, create_model

from denckring.core import catalogue
from denckring.core.errors import DegenerateOutput, InvalidParams, MissingCapability
from denckring.core.prosody import UnknownRhyme
from denckring.core.protocol import Lang, LanguagePack, Meta, Report, Violation

P = TypeVar("P", bound=BaseModel)
A = TypeVar("A", bound=BaseModel)


class DiacriticParams(BaseModel):
    """Mixed into every procedure that compares letters.

    Whether `Mädchen` belongs in an a-lipogram is an editorial decision, not a
    library constant — Perec's translators had to make it too. Carrying it as a
    parameter puts it in `params_schema()` and on the command line for free.
    """

    fold_diacritics: bool = Field(
        default=True,
        description="Treat accented letters as their base letter, and ß as ss.",
    )


class RhymeParams(BaseModel):
    """Mixed into every procedure that checks a rhyme.

    Whether a word the pronouncing dictionary does not carry rhymes is an
    editorial decision rather than a library constant — the same argument
    `DiacriticParams` makes about `Mädchen`. Carrying it as a parameter puts it
    in `params_schema()` and on the command line for free, so a caller can say
    what an unknown word should mean for their text instead of inheriting a
    guess. `denckring.core.prosody.scheme_violations` documents the readings.
    """

    unknown_rhyme: UnknownRhyme = Field(
        default="undecidable",
        description=(
            "What a line ending absent from the pronouncing dictionary means: "
            "leave the pair unscored (undecidable), let it satisfy the scheme "
            "(free), or fail it (strict)."
        ),
    )


class SourceParams(BaseModel):
    """Mixed into procedures decidable only against the text they were made from.

    Carried as a parameter rather than a second argument to `check`, so the
    signature stays one-text and the requirement shows up in `params_schema()`
    for callers that never touch Python.
    """

    source: str = Field(description="The text this one was made from.")


class SeedParams(BaseModel):
    """Mixed into every procedure that draws at random.

    A field, not a signature keyword. `Constructive.apply` used to name `seed`
    explicitly, and Python binds a keyword matching an explicit parameter to that
    parameter before any of it reaches `**params` — silently. So `seed` reached
    no params model, pydantic never typed it, and all 27 generators accepted
    `seed="not-an-int"`. `diastic` documented the collision and renamed its own
    field around it; this removes the collision instead.

    Carried only by the ten procedures that draw, so `seed` cannot be passed to
    the other seventeen at all — the same exclusion-by-type ADR 0009 gives
    `fold_diacritics`.
    """

    seed: int | None = Field(default=None, description="Fixes the draw, for a repeatable result.")


class ApplyParams(BaseModel):
    """Mixed into every generator's apply-params model.

    A generator that returns its input has not run the procedure, and says
    nothing a caller can act on. Refusing it is the default; `allow_identity`
    is for the caller who genuinely wants the degenerate case.

    No field here, or on any model this mixes into, may be named `lang`:
    `ConstructiveProcedure.apply` still takes `lang` as an explicit signature
    keyword, and Python binds a keyword matching an explicit parameter name to
    that parameter before any of it reaches `**params` — silently, the same
    collision `seed` used to carry before `SeedParams` closed it for that name
    alone.
    """

    allow_identity: bool = Field(
        default=False,
        description=(
            "Permit output identical to the input, which normally means the procedure did not run."
        ),
    )


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

    def parse_params(self, params: dict[str, Any]) -> P:
        """Validate parameters, raising `InvalidParams` like `check` does.

        `apply` used to call `model_validate` directly, so a missing parameter
        escaped as a Pydantic error rather than a DenckringError — which meant
        callers had to catch two kinds of failure for one kind of mistake.
        """
        return cast(P, parse_into(self.params_model(), params, self.id))

    def params_schema(self) -> dict[str, Any]:
        """JSON Schema for the parameters, for non-Python callers."""
        return self.params_model().model_json_schema()

    def check(self, text: str, *, lang: Lang = "en", **params: Any) -> Report:
        """Validate a text against this procedure."""
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in self.meta.requires:
            require_capability(pack, capability, self.id)
        # Silently dropping a mistyped parameter would let a caller believe a
        # constraint was applied when it was not, so parse_params refuses it.
        return self._check(text, pack, self.parse_params(params))

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


def parse_into(model: type[BaseModel], params: dict[str, Any], procedure_id: str) -> BaseModel:
    """Validate `params` against `model`, raising `InvalidParams` either way.

    Extracted from `BaseProcedure.parse_params` so `apply` validates by exactly
    the rule `check` does. Silently dropping a mistyped parameter would let a
    caller believe a constraint was applied when it was not.
    """
    unknown = sorted(set(params) - set(model.model_fields))
    if unknown:
        raise InvalidParams(
            procedure_id,
            f"unknown parameter(s) {unknown}; this procedure accepts {sorted(model.model_fields)}",
        )
    try:
        return model.model_validate(params)
    except ValidationError as exc:
        raise InvalidParams(procedure_id, str(exc)) from exc


def require_capability(pack: LanguagePack, capability: str, procedure_id: str) -> None:
    """Raise `MissingCapability` unless the pack declares it."""
    if capability not in pack.capabilities:
        raise MissingCapability(procedure_id, pack.lang, capability)


class ConstructiveProcedure(BaseProcedure[P], Generic[P, A]):
    """A procedure that generates as well as checks.

    `apply` is the template method `check` has always had: it resolves the pack,
    enforces both capability lists, validates parameters, and refuses output
    identical to the input — so an individual procedure module cannot forget any
    of it. ADR 0002 is amended rather than reversed: `apply` is still optional,
    but a procedure that has one inherits this.
    """

    #: Set on a generator whose `_apply` never reads `text`: the three devices
    #: that supply everything themselves — `denckring`, `poesie_automat` and
    #: `llull_figure` — turn rings, press a button or spin a wheel, and the
    #: argument is there only because `apply` takes one. `_guard_degenerate`
    #: skips the identity comparison for them, because comparing output against
    #: an argument the procedure never read carries no information at all:
    #: `denckring.apply("geRyffisch", seed=3)` spelling `geRyffisch` again is
    #: the rings coming up the same way, not a procedure that failed to run,
    #: and refusing it turns the explorer's invitation to paste output back in
    #: into an error. The empty-output half of the guard still applies.
    ignores_input: ClassVar[bool] = False

    @classmethod
    def apply_params_model(cls) -> type[A]:
        """The parameters `apply` accepts.

        Defaults to the checker's model widened by `ApplyParams`. A generator
        with parameters of its own — a seed, a target word — declares its own
        model and inherits `ApplyParams` explicitly.
        """
        combined = create_model(
            f"{cls.__name__}ApplyParams", __base__=(cls.params_model(), ApplyParams)
        )
        return cast(type[A], combined)

    def parse_apply_params(self, text: str, params: dict[str, Any]) -> A:
        """Validate, supplying `source` from the text being transformed.

        Every generator did this by hand as `parse_params({"source": text,
        **params})`. Doing it here is what makes it impossible to forget — and
        is the only place that can refuse a caller who supplies a second source.
        """
        model = self.apply_params_model()
        if "source" in model.model_fields:
            # Refused rather than overridden in either direction. The text being
            # transformed *is* the source, so a second one names two different
            # sources and only one can be honoured — and honouring one silently
            # is the mistake `parse_into` exists to refuse.
            if "source" in params:
                raise InvalidParams(
                    self.id,
                    "source is the text this generates from, which `apply` already has "
                    "as its text argument; passing both names two sources and leaves "
                    "no way to say which was used",
                )
            params = {"source": text, **params}
        return cast(A, parse_into(model, params, self.id))

    @abstractmethod
    def _apply(self, text: str, pack: LanguagePack, params: A) -> str:
        """Procedure-specific generation. Language and parameters are already valid."""

    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
        """Generate text with this procedure."""
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in (*self.meta.requires, *self.meta.apply_requires):
            require_capability(pack, capability, self.id)
        parsed = self.parse_apply_params(text, params)
        return self._guard_degenerate(text, self._apply(text, pack, parsed), parsed)

    def _guard_degenerate(self, text: str, produced: str, params: A) -> str:
        """Refuse output identical to the input.

        Compared on stripped text, because trailing whitespace is not a
        transformation. Skipped entirely for a procedure that declares
        `ignores_input`. `allow_identity` is on `ApplyParams`, so every generator
        carries the escape whether or not it declares its own model — read with
        `getattr` because a generator may declare an apply-params model that
        does not inherit the mixin.
        """
        if getattr(params, "allow_identity", False):
            return produced
        if not self.ignores_input and produced.strip() == text.strip():
            raise DegenerateOutput(self.id)
        return produced
