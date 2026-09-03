"""Kangaroo word — a word carrying a synonym of itself in its own letters.

*Encourage* hides *urge*; *masculine* hides *male*. The letters must appear in
order, though not adjacently — that scattering is the form.

**Whether the two words are synonyms is the writer's claim, not this checker's
finding.** A thesaurus cannot settle it: WordNet's synonymy is synset
co-membership, which rejects *encourage*/*urge* and *masculine*/*male* while
accepting spelling variants like *abcs*/*abc*. So the synonym is a parameter,
and what this row verifies is the decidable half — that the claimed synonym is a
real word, that it is not the word itself, and that its letters appear in order.
`univocalic_translation` treats its own undecidable half the same way.
"""

from __future__ import annotations

from pydantic import Field

from denckring.core.base import BaseProcedure, DiacriticParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register


class KangarooWordParams(DiacriticParams):
    synonym: str = Field(description="The synonym the word is claimed to carry.")


def _in_order(needle: str, haystack: str) -> bool:
    letters = iter(haystack)
    return all(character in letters for character in needle)


@register
class KangarooWord(BaseProcedure[KangarooWordParams]):
    """The decidable half of the form: a real word, hidden in order, not itself."""

    id = "kangaroo_word"

    @classmethod
    def params_model(cls) -> type[KangarooWordParams]:
        return KangarooWordParams

    def _check(self, text: str, pack: LanguagePack, params: KangarooWordParams) -> Report:
        def fold(ch: str) -> str:
            return pack.fold_diacritics(ch) if params.fold_diacritics else ch.lower()

        host = "".join(fold(ch) for ch in text if ch.isalpha())
        synonym = "".join(fold(ch) for ch in params.synonym if ch.isalpha())
        violations: list[Violation] = []
        good = 0
        total = 3

        # `is_word` is not fold-aware -- French keeps its accents on purpose
        # (ADR 0009), so a diacritic-folded "ecole" could never match the
        # table's "école". Checked on the parameter as written, casefolding
        # only -- the way `paragram` and `word_ladder` already call `is_word`
        # -- rather than on `synonym`, which is folded for the distinctness
        # and ordering checks below. ADR 0036.
        if pack.is_word(params.synonym):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="not_a_word",
                    offset=None,
                    found=params.synonym,
                    expected="a word the lexicon knows",
                )
            )

        if synonym and synonym != host:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="synonym_is_the_word",
                    offset=None,
                    found=params.synonym,
                    expected="a different word",
                )
            )

        if _in_order(synonym, host):
            good += 1
        else:
            violations.append(
                Violation(
                    rule="synonym_not_in_order",
                    offset=0,
                    found=params.synonym,
                    expected=f"letters appearing in order within {text!r}",
                )
            )

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={"hidden_letters": float(len(synonym))},
        )
