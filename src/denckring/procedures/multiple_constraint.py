"""Multiple constraint — a text satisfying two or more named constraints at once.

Renamed from `univocalic_lipogram_pair`: that id named one pair of constraints,
but the form Oulipo describes is generic over any two or more. This row is the
generic combinator — `constraints` names any already-registered procedures,
`constraint_params` carries what each one needs, and the composite is satisfied
only when every named constraint's own `check` is.

Two things follow from being generic rather than fixed, unlike `univocalic_translation`
and `lipogrammatic_translation`, which each delegate to one specific, known procedure:

**Capabilities cannot be declared statically.** The catalogue's `requires: [tokens]`
for this row describes what *this* procedure needs to run its own logic — nothing
more. If a caller names `haiku` among `constraints`, the composite as configured
needs `syllables.heuristic` too, but that is not knowable until `constraints` is
read at call time, and a different call might name something else entirely. So
this row does not attempt to declare the union of its delegates' requirements; it
declares only its own, and lets each named constraint's `MissingCapability` (from
`BaseProcedure.check`'s own `require_capability` call, unmodified) propagate
uncaught, naming the delegate and the capability it actually lacks rather than a
confusing failure blamed on `multiple_constraint` itself. `describe_procedure`
reporting `requires: [tokens]` for this row is correct and must not be read as a
promise that every composition it could run is covered by that alone.

**A generic `good`/`total` cannot be read from an arbitrary delegate's `metrics`.**
`univocalic_translation` reads `metrics["vowel_count"]`/`["foreign"]` because it
always delegates to `univocalic`, a fixed, known procedure whose metric keys are
pinned by a test. `multiple_constraint` delegates to whatever `constraints` names,
and a survey of this codebase's ~110 procedures turns up no shared metric key
convention — `words`/`out_of_order`, `letters`/`hits`, `vowel_count`/`foreign`,
`units`/`wrong`, `lines`/`wrong`, and more, none of them universal. Guessing at a
delegate's internal accounting from an unfamiliar key name would be worse than not
trying. So this row does not invert an arbitrary delegate's float `score` (which
would only approximate the delegate's own counts, the exact failure mode
`univocalic_translation` was fixed to avoid) and does not attempt to parse its
`metrics` either. Instead each named constraint contributes one exact, lossless
unit to this row's own accounting: `good += 1` iff the delegate's own `satisfied`
is `True`, out of `total = len(constraints)`. `satisfied == (score == 1.0)` holds
exactly, matching "satisfied only when all are." Each delegate's own `score` is
still recorded, per constraint, in `metrics` for anyone wanting finer detail than
a satisfied/unsatisfied count.

**Recursion.** `constraints` naming `multiple_constraint` itself — directly, or
nested one level into `constraint_params` for a different named constraint that is
itself `multiple_constraint` again — is unbounded: this procedure is a singleton
(one registered instance under the id `multiple_constraint`), so there is no way
for a *different* procedure to stand in the middle of a cycle back to it. Every
call, at every depth, validates its own `constraints` through the same
`field_validator` below, so a self-reference is refused with `InvalidParams`
naming the cycle at the shallowest level it appears — before that level's `_check`
runs, let alone any level nested inside it. That also means a two-hop chain (the
self-reference sitting inside `constraint_params` rather than the outer
`constraints` list) is not, in fact, constructible as anything other than the same
one-level check catching it at whichever level names `multiple_constraint`; the
tests cover both the bare case and one with the self-reference alongside a
legitimate constraint, plus a nested one that is never reached because the outer
level's own list already contains the name.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import get, register

#: This row's own id, checked against `constraints` at validation time. A literal
#: rather than `cls.id` inside the validator: `field_validator` runs as part of
#: model construction, before any procedure instance need exist.
_SELF_ID = "multiple_constraint"


class MultipleConstraintParams(BaseModel):
    constraints: list[str] = Field(
        min_length=2,
        description="Ids of already-registered procedures this text must jointly satisfy.",
    )
    constraint_params: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Per-constraint parameters, keyed by the constraint's id in `constraints`.",
    )

    @field_validator("constraints")
    @classmethod
    def _no_self_reference(cls, value: list[str]) -> list[str]:
        if _SELF_ID in value:
            raise ValueError(
                f"constraints cannot name {_SELF_ID!r} — recursive composition is not "
                f"supported (cycle: {_SELF_ID} -> {_SELF_ID})"
            )
        return value


@register
class MultipleConstraint(BaseProcedure[MultipleConstraintParams]):
    """Every named constraint's own `check`, combined; satisfied only if all are."""

    id = "multiple_constraint"

    @classmethod
    def params_model(cls) -> type[MultipleConstraintParams]:
        return MultipleConstraintParams

    def _check(self, text: str, pack: LanguagePack, params: MultipleConstraintParams) -> Report:
        violations: list[Violation] = []
        metrics: dict[str, float] = {"constraints": float(len(params.constraints))}
        good = 0
        for constraint_id in params.constraints:
            delegate = get(constraint_id)
            sub_params = params.constraint_params.get(constraint_id, {})
            report = delegate.check(text, lang=pack.lang, **sub_params)
            if report.satisfied:
                good += 1
            metrics[f"{constraint_id}_score"] = report.score
            for violation in report.violations:
                note = (
                    constraint_id
                    if violation.note is None
                    else f"{constraint_id}: {violation.note}"
                )
                violations.append(violation.model_copy(update={"note": note}))
        metrics["satisfied_constraints"] = float(good)
        return self._report(
            good=good,
            total=len(params.constraints),
            violations=violations,
            metrics=metrics,
        )
