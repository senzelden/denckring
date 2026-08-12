"""Wechselsatz — each word drawn from the alternatives for its position."""

from __future__ import annotations

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.procedures.cent_mille_milliards import SEPARATOR


class WechselsatzParams(SourceParams):
    pass


@register
class Wechselsatz(BaseProcedure[WechselsatzParams]):
    """Kuhlmann's permutation poem, checked one word at a time.

    The source is the template: alternatives for each position separated by a
    bar, positions separated by whitespace. `Der Wechsel Menschlicher Sachen`
    claims millions of readings from a fixed frame, and the frame is what this
    verifies against.
    """

    id = "wechselsatz"

    @classmethod
    def params_model(cls) -> type[WechselsatzParams]:
        return WechselsatzParams

    def _check(self, text: str, pack: LanguagePack, params: WechselsatzParams) -> Report:
        offered = [
            [part.strip().casefold() for part in slot.split(SEPARATOR) if part.strip()]
            for slot in params.source.split()
        ]
        chosen = word_spans(text, pack)
        violations: list[Violation] = []
        matched = 0
        for index, options in enumerate(offered):
            if index >= len(chosen):
                violations.append(
                    Violation(
                        rule="missing_word",
                        offset=None,
                        found="",
                        expected=f"one of {'/'.join(options)}",
                    )
                )
                continue
            offset, word = chosen[index]
            if word.casefold() in options:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="word_not_offered",
                        offset=offset,
                        found=word,
                        expected=f"one of {'/'.join(options)}",
                    )
                )
        for offset, word in chosen[len(offered) :]:
            violations.append(Violation(rule="extra_word", offset=offset, found=word, expected=""))
        combinations = 1
        for options in offered:
            combinations *= max(len(options), 1)
        return self._report(
            good=matched,
            total=max(len(offered), len(chosen)),
            violations=violations,
            metrics={"positions": float(len(offered)), "combinations": float(combinations)},
        )
