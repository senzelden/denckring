"""N+7 — every noun replaced by the seventh noun after it in the dictionary."""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


class NPlus7Params(SourceParams):
    offset: int = Field(default=7, description="How many nouns to count forward.")


def displacement_report(
    procedure: BaseProcedure[NPlus7Params],
    text: str,
    pack: LanguagePack,
    params: NPlus7Params,
) -> Report:
    """Check a noun-displacement of a source, tolerating part-of-speech ambiguity.

    A word list cannot tell you that *run* is a verb in this sentence. So an
    unchanged word that happens to be in the noun list is accepted — it may well
    be a verb there — and the count of such positions is reported, in the same
    way `estimated_words` keeps the syllable heuristic honest.
    """
    candidate = word_spans(text, pack)
    source = word_spans(params.source, pack)
    nouns = pack.nouns()
    violations: list[Violation] = []

    if len(candidate) != len(source):
        return procedure._report(
            good=0,
            total=1,
            violations=[
                Violation(
                    rule="wrong_word_count",
                    offset=None,
                    found=f"{len(candidate)} words",
                    expected=f"{len(source)} words",
                )
            ],
            metrics={"words": float(len(candidate)), "ambiguous_words": 0.0},
        )

    ambiguous = 0
    good = 0
    for (offset, produced), (_, original) in zip(candidate, source, strict=True):
        index = pack.noun_index(original)
        if produced.casefold() == original.casefold():
            if index is None:
                good += 1
            else:
                # Listed as a noun but left alone: readable as another part of
                # speech here, which no word list can rule out.
                ambiguous += 1
                good += 1
            continue
        if index is None:
            violations.append(
                Violation(
                    rule="changed_a_non_noun",
                    offset=offset,
                    found=produced,
                    expected=original,
                )
            )
            continue
        expected = nouns[(index + params.offset) % len(nouns)]
        if produced.casefold() == expected:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="wrong_displacement",
                    offset=offset,
                    found=produced,
                    expected=expected,
                )
            )
    return procedure._report(
        good=good,
        total=max(len(candidate), 1),
        violations=violations,
        metrics={"words": float(len(candidate)), "ambiguous_words": float(ambiguous)},
    )


@register
class NPlus7(BaseProcedure[NPlus7Params]):
    """Lescure's procedure: walk the dictionary seven nouns on."""

    id = "n_plus_7"

    @classmethod
    def params_model(cls) -> type[NPlus7Params]:
        return NPlus7Params

    def _check(self, text: str, pack: LanguagePack, params: NPlus7Params) -> Report:
        return displacement_report(self, text, pack, params)
