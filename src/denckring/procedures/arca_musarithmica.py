"""Arca musarithmica — a phrase set from the tablet for its length."""

from __future__ import annotations

import random

from pydantic import Field

from denckring.core import arca
from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, SourceParams
from denckring.core.errors import UnsettablePhrase
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans
from denckring.procedures.syllable_count import line_syllables


class ArcaMusarithmicaParams(SourceParams):
    pinakes: str = Field(description="The pattern tablets, as JSON.")
    syntagma: str = Field(
        default=arca.DEFAULT_SYNTAGMA,
        description="Which tablet to draw from; Kircher's first is plain, his second florid.",
    )
    tonus: str | None = Field(default=None, description="The mode, if the table names any.")


class ArcaMusarithmicaApplyParams(ArcaMusarithmicaParams, SeedParams, ApplyParams):
    pass


@register
class ArcaMusarithmica(ConstructiveProcedure[ArcaMusarithmicaParams, ArcaMusarithmicaApplyParams]):
    """Kircher's box, kept to the part that is about writing.

    One phrase per line in the source; one chosen pattern per line in the text
    under check. Each phrase's syllables are counted, and the pattern must be one
    the tablet offers for a phrase of that length.

    The patterns are never read. Kircher's are pitches and rhythms; put stress
    patterns or rhyme schemes in the same table and the machine still works,
    which is the whole reason to implement the indexing rather than the music.
    A phrase whose length the tablet does not cover is reported as unsettable —
    Kircher's rods run to particular lengths and a text that exceeds them simply
    cannot be set by that box.
    """

    id = "arca_musarithmica"

    @classmethod
    def params_model(cls) -> type[ArcaMusarithmicaParams]:
        return ArcaMusarithmicaParams

    def _check(self, text: str, pack: LanguagePack, params: ArcaMusarithmicaParams) -> Report:
        tablets = arca.parse(params.pinakes)
        measured = line_syllables(params.source, pack)
        chosen = [line.strip() for _, line in line_spans(text)]

        violations: list[Violation] = []
        matched = 0
        checks = 0
        estimated = sum(estimate for _, _, estimate in measured)

        # Counted, not merely appended: a violation the score never sees would
        # let the report say satisfied while listing what was wrong.
        if params.tonus is not None and tablets.tones:
            checks += 1
            if params.tonus in tablets.tones:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="unknown_tone",
                        offset=None,
                        found=params.tonus,
                        expected=f"one of {', '.join(tablets.tones)}",
                    )
                )

        for index, (_, syllables, _) in enumerate(measured):
            offered = tablets.patterns(syllables, params.syntagma)
            if not offered:
                violations.append(
                    Violation(
                        rule="no_tablet_for_length",
                        offset=None,
                        found=f"a phrase of {syllables} syllables",
                        expected=f"a length the tablet covers: {tablets.lengths(params.syntagma)}",
                        note="the box cannot set a phrase of this length at all",
                    )
                )
                continue
            if index >= len(chosen):
                violations.append(
                    Violation(
                        rule="phrase_not_set",
                        offset=None,
                        found="",
                        expected=f"one of {len(offered)} patterns for {syllables} syllables",
                    )
                )
                continue
            if chosen[index] in offered:
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="pattern_not_on_the_tablet",
                        offset=None,
                        found=chosen[index],
                        expected=f"one of the {len(offered)} patterns for {syllables} syllables",
                    )
                )
        for extra in chosen[len(measured) :]:
            violations.append(
                Violation(rule="pattern_without_phrase", offset=None, found=extra, expected="")
            )

        total = checks + max(len(measured), len(chosen), 1)
        return self._report(
            good=matched,
            total=total,
            violations=violations,
            metrics={
                "phrases": float(len(measured)),
                "estimated_words": float(estimated),
                "settable_lengths": float(len(tablets.lengths(params.syntagma))),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[ArcaMusarithmicaApplyParams]:
        return ArcaMusarithmicaApplyParams

    def _produce(
        self, text: str, pack: LanguagePack, params: ArcaMusarithmicaApplyParams
    ) -> list[str]:
        """Set `text`, one pattern per phrase, drawn from the tablet for its length."""
        tablets = arca.parse(params.pinakes)
        chooser = random.Random(params.seed)
        setting: list[str] = []
        for _, syllables, _ in line_syllables(text, pack):
            offered = tablets.patterns(syllables, params.syntagma)
            if not offered:
                raise UnsettablePhrase(syllables, tablets.lengths(params.syntagma))
            setting.append(chooser.choice(offered))
        return ["\n".join(setting)]
