"""The template method every procedure inherits.

`check` validates language, capability and parameters before delegating, so an
individual procedure module cannot forget those checks. `ConstructiveProcedure`
gives `apply` the same spine, which it went without because ADR 0002 made it
optional and so kept it off `BaseProcedure` entirely.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, Field, ValidationError

from denckring.core import catalogue
from denckring.core.errors import DegenerateOutput, InvalidParams, MissingCapability
from denckring.core.prosody import UnknownRhyme
from denckring.core.protocol import (
    Candidate,
    Lang,
    LanguagePack,
    Meta,
    Produced,
    Production,
    Report,
    Violation,
)

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

    A generator that returns its input — or returns nothing at all — has not
    run the procedure in any way a caller can act on. Refusing both is the
    default; `allow_identity` is the one escape for the caller who genuinely
    wants the degenerate case, under either of its two shapes.

    No field here, or on any model this mixes into, may be named `lang`:
    `ConstructiveProcedure.produce` and `apply` both take `lang` as an explicit
    signature keyword — `produce` is where the collision would actually bind,
    since `apply` only forwards its own `lang` keyword through — and Python
    binds a keyword matching an explicit parameter name to that parameter
    before any of it reaches `**params` — silently, the same collision `seed`
    used to carry before `SeedParams` closed it for that name alone.

    `max_results` defaults to ten rather than one because a caller asking a
    procedure that has many valid answers expects more than one of them, and
    rather than unbounded because `dormitory` alone has thirty-two exact
    two-word covers before any deeper search. `Production.truncated` is what
    keeps a capped search from reading as an exhaustive one.
    """

    allow_identity: bool = Field(
        default=False,
        description=(
            "Permit output identical to the input, or empty, which normally "
            "means the procedure did not run."
        ),
    )
    max_results: int = Field(
        default=10,
        ge=1,
        description="How many results to return at most. `apply` returns the first.",
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


def plain(texts: Iterable[str]) -> Produced:
    """Candidates with nothing known about them beyond their text.

    Twenty-six of the twenty-seven generators are in this case and say so in one
    call, rather than each spelling out a `Candidate(text=...)` comprehension.
    ADR 0027 changed the primitive's type; it did not claim every procedure
    suddenly has a score, or that any of them ran out of budget.
    """
    return Produced(candidates=[Candidate(text=text) for text in texts])


def require_capability(pack: LanguagePack, capability: str, procedure_id: str) -> None:
    """Raise `MissingCapability` unless the pack declares it."""
    if capability not in pack.capabilities:
        raise MissingCapability(procedure_id, pack.lang, capability)


class ConstructiveProcedure(BaseProcedure[P], Generic[P, A]):
    """A procedure that generates as well as checks.

    `produce` is the template method `check` has always had: it resolves the
    pack, enforces both capability lists, validates parameters, and filters
    output that misrepresents what ran — identical to the input, or empty —
    so an individual procedure module cannot forget any of it. `apply` is the
    one-text surface defined on top: `produce(...).texts[0]`, for a caller who
    wants the best answer and not the search behind it. ADR 0002 is amended
    rather than reversed: `apply` is still optional, but a procedure that has
    one inherits both.
    """

    #: Set on a generator whose `_produce` never reads `text`: the three devices
    #: that supply everything themselves — `denckring`, `poesie_automat` and
    #: `llull_figure` — turn rings, press a button or spin a wheel, and the
    #: argument is there only because `apply` takes one. `_is_degenerate`
    #: skips the identity comparison for them, because comparing output against
    #: an argument the procedure never read carries no information at all:
    #: `denckring.apply("geRyffisch", seed=3)` spelling `geRyffisch` again is
    #: the rings coming up the same way, not a procedure that failed to run,
    #: and refusing it turns the explorer's invitation to paste output back in
    #: into an error. The empty-output half of the guard still applies.
    ignores_input: ClassVar[bool] = False

    @classmethod
    @abstractmethod
    def apply_params_model(cls) -> type[A]:
        """The parameters `apply` accepts.

        Declared, not defaulted. This used to synthesise the checker's model
        widened by `ApplyParams` via `create_model`, and every one of the 27
        generators overrides it anyway — `mypy --strict` wants a named class to
        annotate `_produce`'s `params` with — so the default had no production
        caller, its only coverage was a test double built to reach it, and it
        carried an MRO trap for any `params_model()` returning `BaseModel`
        itself. A generator declares `<Name>ApplyParams`, inheriting its own
        params model and `ApplyParams`, plus `SeedParams` if it draws.
        """

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
    def _produce(self, text: str, pack: LanguagePack, params: A) -> Produced:
        """Procedure-specific generation, best first. Language and parameters are already valid.

        Ordered even where there is one answer: `apply` returns `texts[0]`, so the
        order is the contract, and a generator that ranks its candidates puts its
        winner at the front. One primitive rather than a `str` one beside a
        `list` one, because two would make every consumer ask which a given
        procedure implements.

        `Produced` and not `list[str]` since ADR 0027, for two reasons that arrived
        together: a generator that ranks needs somewhere to put the number it
        ranked by, and a generator that abandons its own budget needs somewhere to
        say so — the spine cannot derive the second, because giving up makes the
        result set smaller and its own test is whether the set was too large.
        Generators with neither wrap their strings with `plain()`.
        """

    def produce(self, text: str, *, lang: Lang = "en", **params: Any) -> Production:
        """Generate with this procedure, returning every result it found.

        Carries the preamble `apply` used to: `apply` is now defined in terms of
        this, so there is one path through the pack, the capabilities, the
        parameters and the guard rather than two that can drift.
        """
        from denckring.lang import get_pack

        pack = get_pack(lang)
        for capability in (*self.meta.requires, *self.meta.apply_requires):
            require_capability(pack, capability, self.id)
        parsed = self.parse_apply_params(text, params)
        produced = self._produce(text, pack, parsed)
        if not produced.candidates:
            # Checked before `_guard_degenerate`, and not through it, so
            # `allow_identity` cannot waive it: that flag exists for a caller who
            # wants the degenerate-but-real result a procedure found, and an
            # empty list is not a result at all — there is nothing to want.
            # Left to `_guard_degenerate`, `observed` would default to IDENTICAL,
            # which is false (nothing was produced to compare), and with
            # `allow_identity=True` the empty list would reach `Production.texts`
            # and fail its `min_length=1` as a bare pydantic `ValidationError` —
            # not a `DenckringError`, so it would escape the MCP server's handler
            # uncaught.
            raise DegenerateOutput(self.id, DegenerateOutput.NOTHING)
        found = self._guard_degenerate(text, produced.candidates, parsed)
        # `getattr`, falling back to one rather than ten, for the reason
        # `_guard_degenerate` reads `allow_identity` the same way: a generator
        # may declare an apply-params model that does not inherit `ApplyParams`,
        # and the safe reading of a missing limit is the old single-result
        # behaviour rather than a larger one it never asked for.
        limit = getattr(parsed, "max_results", 1)
        return Production(
            procedure=self.id,
            candidates=found[:limit],
            # Either event means the same thing to a reader — what you were shown
            # is not everything — but only one of them is visible from here.
            truncated=produced.truncated or len(found) > limit,
            metrics={"found": float(len(found))},
        )

    def apply(self, text: str, *, lang: Lang = "en", **params: Any) -> str:
        """Generate one text with this procedure — the best one it found.

        One and not several: `check` reads what `apply` returned as a single
        text, so three anagrams joined by newlines are a text with three times
        the letters, which its own checker scores 0.333. The round-trip property
        that has guarded every generator here through two migrations depends on
        this staying one text. `produce` is where the rest go.
        """
        return self.produce(text, lang=lang, **params).texts[0]

    def _guard_degenerate(self, text: str, produced: list[Candidate], params: A) -> list[Candidate]:
        """Refuse output that says nothing about what the procedure did.

        `allow_identity` is on `ApplyParams`, so every generator carries the
        escape whether or not it declares its own model — read with `getattr`
        because a generator may declare an apply-params model that does not
        inherit the mixin.

        When nothing survives, `observed` still distinguishes empty from
        identical rather than collapsing to one generic message: a
        single-candidate generator — every one of them, until Task 3 — has
        exactly one candidate to have judged degenerate, so this reports the
        same shape `_is_degenerate` saw for it, in the same priority it
        checked in, and the caller reading `detail()["observed"]` after this
        split learns what it learned before.
        """
        if getattr(params, "allow_identity", False):
            return produced
        kept = [
            candidate for candidate in produced if not self._is_degenerate(text, candidate.text)
        ]
        if kept:
            return kept
        observed = (
            DegenerateOutput.EMPTY
            if text.strip() and any(not candidate.text.strip() for candidate in produced)
            else DegenerateOutput.IDENTICAL
        )
        raise DegenerateOutput(self.id, observed)

    def _is_degenerate(self, text: str, produced: str) -> bool:
        """One candidate's worth of the judgement the guard used to make wholesale.

        Filtering rather than refusing is what a multi-result generator needs: an
        anagram search that finds its own source among the covers should drop
        that one and return the others, not fail the call. For a generator with
        one candidate the two are the same thing — nothing survives, so the
        guard raises exactly as before.

        Two shapes. Output identical to the input is the one the guard was
        built for; the identity comparison is skipped for a procedure that
        declares `ignores_input`, where it compares against an argument that
        was never read.

        Empty output from input that was not empty is the same defect and was
        left open: `_report` scores an empty text 1.0 — vacuously satisfied, as
        its own docstring says — so `melting_text.apply("hello", seed=0)`
        returning `""` passed every gate this project runs, which is the thesis
        of this check in its second half. Refused under the same error and the
        same escape, because a caller cannot act differently on the two.

        Both are compared on stripped text, because trailing whitespace is
        neither a transformation nor content.
        """
        if not produced.strip() and text.strip():
            return True
        return not self.ignores_input and produced.strip() == text.strip()
