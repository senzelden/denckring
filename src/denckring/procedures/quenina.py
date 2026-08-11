"""Quenina — end-words rotate by the spiral permutation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core.base import BaseProcedure
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans


def spiral(size: int) -> list[int]:
    """The permutation a quenina applies to its end-words between stanzas.

    Reading from the outside in and alternating ends: for six words it gives
    6-1-5-2-4-3, the sestina's rotation.
    """
    order: list[int] = []
    low, high = 0, size - 1
    while low <= high:
        order.append(high)
        high -= 1
        if low <= high:
            order.append(low)
            low += 1
    return order


def is_valid_size(size: int) -> bool:
    """True when iterating the spiral `size` times returns every word home."""
    if size < 1:
        return False
    permutation = spiral(size)
    current = list(range(size))
    for step in range(1, size + 1):
        current = [current[index] for index in permutation]
        if current == list(range(size)):
            return step == size
    return False


def end_words(text: str, pack: LanguagePack) -> list[str]:
    return [words[-1].casefold() for _, line in line_spans(text) if (words := pack.tokenize(line))]


class QueninaParams(BaseModel):
    n: int | None = Field(default=None, description="Words per stanza; inferred if unset.")


@register
class Quenina(BaseProcedure[QueninaParams]):
    """Queneau and Roubaud's generalisation of the sestina.

    Checks the end-word permutation only, not metre or rhyme — the catalogue
    definition says the same, so the row promises nothing the code skips.
    """

    id = "quenina"

    @classmethod
    def params_model(cls) -> type[QueninaParams]:
        return QueninaParams

    def _check(self, text: str, pack: LanguagePack, params: QueninaParams) -> Report:
        endings = end_words(text, pack)
        if not endings:
            return self._report(good=0, total=0, violations=[], metrics={"lines": 0.0})
        size = params.n if params.n is not None else len(set(endings[: len(endings)])) or 1
        if params.n is None:
            size = next(
                (n for n in range(1, len(endings) + 1) if len(set(endings[:n])) == n), len(endings)
            )
        violations: list[Violation] = []
        if not is_valid_size(size):
            violations.append(
                Violation(
                    rule="invalid_size",
                    offset=None,
                    found=str(size),
                    expected="a size whose spiral permutation has full order",
                )
            )
        permutation = spiral(size)
        expected = endings[:size]
        if len(expected) < size:
            # Fewer lines than the stanza needs: there is no rotation to check.
            return self._report(
                good=len(expected),
                total=size,
                violations=[
                    Violation(
                        rule="missing_line",
                        offset=None,
                        found=f"{len(expected)} lines",
                        expected=f"{size} lines",
                    )
                ],
                metrics={"size": float(size), "lines": float(len(endings))},
            )
        matched = 0
        checked = 0
        for stanza in range(1, size):
            expected = [expected[index] for index in permutation]
            for position in range(size):
                line = stanza * size + position
                if line >= len(endings):
                    violations.append(
                        Violation(
                            rule="missing_line", offset=None, found="", expected=expected[position]
                        )
                    )
                    checked += 1
                    continue
                checked += 1
                if endings[line] == expected[position]:
                    matched += 1
                else:
                    violations.append(
                        Violation(
                            rule="wrong_end_word",
                            offset=None,
                            found=endings[line],
                            expected=expected[position],
                        )
                    )
        matched += size
        checked += size
        if violations and violations[0].rule == "invalid_size":
            checked += 1
        return self._report(
            good=matched,
            total=checked,
            violations=violations,
            metrics={"size": float(size), "lines": float(len(endings))},
        )
