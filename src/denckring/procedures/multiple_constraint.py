"""Multiple constraint — a text satisfying two or more named constraints at once.

Renamed from `univocalic_lipogram_pair`: that id named one pair of constraints,
but the form Oulipo describes is generic over any two or more. This row is the
generic combinator — `constraints` is a list of `{"id": ..., "params": {...}}`,
each naming an already-registered procedure with the parameters it needs, and the
composite is satisfied only when every named constraint's own `check` is.

**The shape is a list of entries, not ids plus a table** (0.4.0, ADR 0059). Until
0.4.0 `constraints` was a list of ids and `constraint_params` a table keyed by id,
so no procedure could appear twice: two lipograms, two acrostics on different
words, could not be composed. Each entry now carries its own parameters, and the
same id may appear more than once. The old shape is refused by `parse_params`
with the call rewritten in the new one, never re-read, so nothing that built the
old shape passes silently with its parameters dropped.

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

**The score is the mean of the constraints' own scores** (ADR 0059, ADR 0005).
Until 0.4.0 each constraint contributed one unit, satisfied or not, so a pair
scored 0, 0.5 or 1 and a text one letter from passing both scored as one that
broke one of them everywhere. The mean reads each delegate's `score` as that
delegate defines it, which is the only account of "how far" a generic composite
can give: no metric key is shared across rows (`words`/`out_of_order`,
`letters`/`hits`, `vowel_count`/`foreign`, ...), and guessing at an unfamiliar
row's accounting would be worse than not trying. It inherits each delegate's own
scale, so a composite of a strict row and a lenient one weighs them as each
weighs itself. `satisfied` is true only when every constraint is, so
`satisfied == (score == 1.0)` holds: a mean of scores in `[0, 1]` is 1.0 exactly
when every score is. `metrics` carries each delegate's verdict and score in
constraint order, under `delegates.<i>.satisfied` and `delegates.<i>.score`
(position-keyed because the same id may appear twice, and flat because `metrics`
holds numbers only; the id at position `i` is the caller's own `constraints[i]`).

**Recursion.** A `constraints` entry naming `multiple_constraint` itself is
unbounded: this procedure is a singleton (one registered instance under the id
`multiple_constraint`), so there is no way for a *different* procedure to stand
in the middle of a cycle back to it. Every call, at every depth, validates its
own `constraints` through the same `field_validator` below, so a self-reference
is refused with `InvalidParams` naming the cycle at the shallowest level it
appears — before that level's `_check` runs, let alone any level nested inside
it. A self-reference nested in an entry's `params` can only sit under an entry
whose own id is `multiple_constraint`, which that level already refuses; the
tests cover the bare case, one alongside a legitimate constraint, and a nested
one that is never reached.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from denckring.core.base import BaseProcedure
from denckring.core.errors import InvalidParams
from denckring.core.fields import param
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import get, register
from denckring.core.scope import Scope, coarsest

#: This row's own id, checked against `constraints` at validation time. A literal
#: rather than `cls.id` inside the validator: `field_validator` runs as part of
#: model construction, before any procedure instance need exist.
_SELF_ID = "multiple_constraint"

#: The largest score below 1.0. A mean of scores each below 1.0 by less than a
#: rounding step can round to 1.0 itself, and `Report` refuses a score of 1.0 that
#: is not satisfied, so an unsatisfied composite's score is capped here.
_BELOW_ONE = math.nextafter(1.0, 0.0)


class Constraint(BaseModel):
    """One constraint a composite text must satisfy: a procedure id and its parameters."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        description="Id of an already-registered procedure.",
        json_schema_extra=param("task", "id"),
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="That procedure's own parameters, as its `check` takes them.",
        json_schema_extra=param("task"),
    )

    def __str__(self) -> str:
        # A hint's `{constraints}` names each constraint by its id; its parameters
        # are stated by the constraint's own hint line (`hint_delegates`, ADR 0050).
        return self.id


class MultipleConstraintParams(BaseModel):
    constraints: list[Constraint] = Field(
        min_length=2,
        description=(
            "The constraints this text must jointly satisfy, in order, each an object "
            '`{"id": procedure id, "params": its parameters}`; an id may appear twice.'
        ),
        json_schema_extra=param("task"),
    )

    @field_validator("constraints")
    @classmethod
    def _no_self_reference(cls, value: list[Constraint]) -> list[Constraint]:
        if any(entry.id == _SELF_ID for entry in value):
            raise ValueError(
                f"constraints cannot name {_SELF_ID!r} — recursive composition is not "
                f"supported (cycle: {_SELF_ID} -> {_SELF_ID})"
            )
        return value


def _old_shape(params: dict[str, Any]) -> str | None:
    """The call rewritten in the 0.4.0 shape, when `params` is in the old one (ADR 0059).

    Refused rather than re-read: a caller still building ids plus `constraint_params`
    learns the new shape from the error, with its own values in it.
    """
    constraints = params.get("constraints")
    named = isinstance(constraints, list) and any(isinstance(c, str) for c in constraints)
    if not named and "constraint_params" not in params:
        return None
    table = params.get("constraint_params")
    table = table if isinstance(table, dict) else {}
    ids = constraints if isinstance(constraints, list) else []
    rewritten = [{"id": c, "params": table.get(c, {})} if isinstance(c, str) else c for c in ids]
    return (
        '`constraints` is a list of {"id": ..., "params": {...}} since 0.4.0, and '
        "`constraint_params` is gone (ADR 0059); this call is "
        f"constraints={json.dumps(rewritten, ensure_ascii=False)}"
    )


def _labels(constraints: list[Constraint]) -> list[str]:
    """How each entry is named in a violation's `note`: its id, with its position when
    the id appears more than once, so two lipograms' violations can be told apart."""
    counts = Counter(entry.id for entry in constraints)
    return [
        entry.id if counts[entry.id] == 1 else f"{entry.id} (constraints[{position}])"
        for position, entry in enumerate(constraints)
    ]


@contextmanager
def _placed(position: int) -> Iterator[None]:
    """A delegate's `InvalidParams`, saying which entry it came from.

    The delegate's own id stays the error's `procedure_id`; the message gains the
    entry's position, which is all that tells two entries with one id apart.
    """
    try:
        yield
    except InvalidParams as exc:
        raise InvalidParams(exc.procedure_id, f"constraints[{position}]: {exc.message}") from exc


@register
class MultipleConstraint(BaseProcedure[MultipleConstraintParams]):
    """Every named constraint's own `check`, combined; satisfied only if all are."""

    id = "multiple_constraint"
    #: Every violation is a delegate's own, carried through with its rule unchanged;
    #: `denckring.rules` answers with every other row's vocabulary.
    rules = ()
    delegates_rules = True
    #: Each entry's `params` is stated by that constraint's own hint line, so
    #: `constraints` is never restated as a setting, whether or not a template
    #: names it.
    hint_delegated = frozenset({"constraints"})

    @classmethod
    def params_model(cls) -> type[MultipleConstraintParams]:
        return MultipleConstraintParams

    def parse_params(self, params: dict[str, Any]) -> MultipleConstraintParams:
        """`BaseProcedure.parse_params`, refusing the pre-0.4.0 shape by name first.

        Without this, `constraint_params` would be refused as an unknown parameter and
        a list of bare ids as a type error, and neither says what to write instead.
        """
        rewritten = _old_shape(params)
        if rewritten is not None:
            raise InvalidParams(self.id, rewritten)
        return super().parse_params(params)

    def hint_delegates(self, params: MultipleConstraintParams) -> list[tuple[str, dict[str, Any]]]:
        """Each constraint with its own parameters, in `constraints` order.

        An entry's `params` changes the task, and only the constraint's own hint can
        state what it says (ADR 0050).
        """
        return [(entry.id, entry.params) for entry in params.constraints]

    def scope(self, params: MultipleConstraintParams) -> Scope:
        """The scope every constraint keeps: satisfied only if all are, so a unit
        every constraint judges alone is judged alone by the composite."""
        scopes: list[Scope] = []
        for position, entry in enumerate(params.constraints):
            with _placed(position):
                delegate = get(entry.id)
                scopes.append(delegate.scope(delegate.parse_params(entry.params)))
        return coarsest(scopes)

    def _check(self, text: str, pack: LanguagePack, params: MultipleConstraintParams) -> Report:
        violations: list[Violation] = []
        metrics: dict[str, float] = {"constraints": float(len(params.constraints))}
        # The constraints' own accounts of what they measured, so `Report.estimated`
        # says of the composite what it says of any constraint inside it. Added, never
        # scored: the verdict and the score below read only the constraints' reports.
        evidence: list[Evidence] = []
        estimated_words = 0.0
        scores: list[float] = []
        good = 0
        labels = _labels(params.constraints)
        for position, entry in enumerate(params.constraints):
            with _placed(position):
                report = get(entry.id).check(text, lang=pack.lang, **entry.params)
            good += report.satisfied
            scores.append(report.score)
            metrics[f"delegates.{position}.satisfied"] = float(report.satisfied)
            metrics[f"delegates.{position}.score"] = report.score
            evidence += report.evidence
            estimated_words += report.metrics.get("estimated_words", 0.0)
            for violation in report.violations:
                label = labels[position]
                note = label if violation.note is None else f"{label}: {violation.note}"
                violations.append(violation.model_copy(update={"note": note}))
        metrics["satisfied_constraints"] = float(good)
        if estimated_words:
            # Only when some constraint estimated, so a composite of exact rows reports
            # exactly the metrics it always has.
            metrics["estimated_words"] = estimated_words
        satisfied = good == len(params.constraints)
        score = sum(scores) / len(scores)
        return Report(
            procedure=self.id,
            satisfied=satisfied,
            score=1.0 if satisfied else min(score, _BELOW_ONE),
            violations=violations,
            metrics=metrics,
            evidence=evidence,
        )
