"""N+7 — every noun replaced by the seventh noun after it in the dictionary."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from denckring.core.base import BaseProcedure, SourceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


def displace(text: str, pack: LanguagePack, offset: int) -> str:
    """Replace each word the noun list knows with the one `offset` further on.

    Word spans are substituted in place rather than re-joined, so punctuation
    and spacing survive — `displacement_report` compares position by position,
    and a generator that normalised the whitespace would produce text its own
    checker then rejected for the wrong reason.
    """
    nouns = pack.nouns()
    pieces: list[str] = []
    cursor = 0
    for offset_in_text, word in word_spans(text, pack):
        index = pack.noun_index(word)
        if index is None:
            continue
        pieces.append(text[cursor:offset_in_text])
        pieces.append(nouns[(index + offset) % len(nouns)])
        cursor = offset_in_text + len(word)
    pieces.append(text[cursor:])
    return "".join(pieces)


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
        # The noun list preserves each language's own capitalisation — German
        # nouns are capitalised, English ones are not — so `expected` must be
        # casefolded too, matching the identity comparison above. Comparing a
        # folded left side to an unfolded right side would silently reject
        # every correct German displacement.
        if produced.casefold() == expected.casefold():
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
        # Not max(..., 1): a text and a source that are both wordless agree
        # vacuously, and forcing the total to 1 made that report unsatisfied
        # while listing no violation — a verdict with nothing behind it. The
        # length mismatch above already fails an empty candidate against a
        # source that has words, which is the case the floor was guarding.
        total=len(candidate),
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

    def apply(self, text: str, *, lang: Lang = "en", seed: int | None = None, **params: Any) -> str:
        """Walk every noun in `text` seven places down the dictionary."""
        from denckring.lang import get_pack

        parsed = self.parse_params({"source": text, **params})
        return displace(text, get_pack(lang), parsed.offset)
