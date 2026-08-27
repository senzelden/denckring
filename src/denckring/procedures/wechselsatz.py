"""Wechselsatz — each word drawn from the alternatives for its position."""

from __future__ import annotations

import random

from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams
from denckring.core.errors import InputTooShort, counted
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.procedures.cent_mille_milliards import SEPARATOR


def drawable(part: str, pack: LanguagePack) -> bool:
    """Is this alternative one word, and the whole of it?

    The frame is read here by splitting on whitespace, but `_check` reads the
    line it produces with `word_spans` — two different tokenizers on the two
    sides of the same comparison. So an alternative the pack reads as no word
    (`'.'`) vanishes from the produced line and the frame checks as short by
    one, and an alternative it reads as two (`'azxb.fam'`) checks as long by
    one: either way `apply` produces text its own `check` rejects. Filtering
    the draw is the narrow fix. Deciding what a well-formed frame may contain
    belongs to the template grammar this row still lacks, and `check` stays
    permissive until that arrives.

    The cost, stated rather than left to be discovered: the pack decides what
    one word is, so a German frame offering `Nacht-Tag` — which the de pack
    reads as two words — silently never draws that alternative. The reader is
    told nothing; the alternative simply cannot come up. That is the same
    silent no-op this chapter abolishes, one level down, and it is carried to
    chapter 2 rather than fixed here: the real answer is a frame contract
    saying what an alternative may be, refused at the door, which is the
    template-grammar work. Refusing here instead would also make every drawn
    example containing `.` refuse, and `wechselsatz` a rare-draw row in the
    coverage property that keeps this migration honest.
    """
    spans = word_spans(part, pack)
    return len(spans) == 1 and spans[0][1] == part


class WechselsatzParams(SourceParams):
    pass


class WechselsatzApplyParams(WechselsatzParams, SeedParams, ApplyParams):
    pass


@register
class Wechselsatz(ConstructiveProcedure[WechselsatzParams, WechselsatzApplyParams]):
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

    @classmethod
    def apply_params_model(cls) -> type[WechselsatzApplyParams]:
        return WechselsatzApplyParams

    def _apply(self, text: str, pack: LanguagePack, params: WechselsatzApplyParams) -> str:
        """One turn of Kuhlmann's frame: a word drawn for each slot.

        The alternatives are read here without folding case — the checker folds
        when comparing, but a generator that lower-cased the whole line would be
        answering a different question than the one the reader asked.
        """
        chooser = random.Random(params.seed)
        # Measured on what the reader wrote, before `drawable` touches it. Filtering
        # first and then counting choices told a reader who had written `'a|. b|.'`
        # that no slot offered a choice and they should add the separator — which
        # they had supplied twice. An error must describe the text it was given.
        offered = [
            [part for part in (raw.strip() for raw in slot.split(SEPARATOR)) if part]
            for slot in text.split()
        ]
        if not any(len(options) > 1 for options in offered):
            raise InputTooShort(
                self.id,
                needed=f"at least one slot offering a choice, separated by {SEPARATOR!r}",
                found=f"{counted(len(offered), 'slot')}, none with a choice",
            )
        slots = [[part for part in options if drawable(part, pack)] for options in offered]
        starved = [written for written, kept in zip(offered, slots, strict=True) if not kept]
        if starved:
            raise InputTooShort(
                self.id,
                needed="every slot to offer at least one alternative that is a single word",
                found=f"{len(starved)} of {counted(len(offered), 'slot')} offering none; the first "
                f"offers only {', '.join(repr(part) for part in starved[0])}",
            )
        return " ".join(chooser.choice(options) for options in slots)
