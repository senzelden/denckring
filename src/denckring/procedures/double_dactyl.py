"""Double dactyl — two quatrains, one line a single double-dactylic word."""

from __future__ import annotations

from pydantic import BaseModel

from denckring.core.base import BaseProcedure
from denckring.core.prosody import stanza_violations
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: Lines 1-3 and 5-7 are double dactyls; lines 4 and 8 close the quatrain.
DOUBLE_DACTYL = "100100"
CLOSE = "1001"

PATTERNS = [[DOUBLE_DACTYL]] * 3 + [[CLOSE]] + [[DOUBLE_DACTYL]] * 3 + [[CLOSE]]

#: The second quatrain is lines 5-8.
SECOND_QUATRAIN = range(4, 8)


class DoubleDactylParams(BaseModel):
    pass


@register
class DoubleDactyl(BaseProcedure[DoubleDactylParams]):
    """Checks the metre and the single double-dactylic word.

    Three clauses of the form are not checked and cannot be. That line one is a
    nonsense phrase is a lexicon question this row does not declare; that line
    two names a person needs an entity recogniser this project does not have;
    and the rhyme between lines four and eight is not checked because this
    definition does not mention it, though the metre already pulls `stress`
    in regardless. A verse failing any of the three is still reported
    satisfied.
    """

    id = "double_dactyl"

    @classmethod
    def params_model(cls) -> type[DoubleDactylParams]:
        return DoubleDactylParams

    def _check(self, text: str, pack: LanguagePack, params: DoubleDactylParams) -> Report:
        result = stanza_violations(text, pack, PATTERNS)
        violations = list(result.violations)
        good = result.good
        total = result.total + 1

        lines = line_spans(text)
        if len(lines) == len(PATTERNS):
            tokens = [pack.tokenize(lines[index][1]) for index in SECOND_QUATRAIN]
            single = [
                index
                for index, words in zip(SECOND_QUATRAIN, tokens, strict=True)
                if len(words) == 1 and pack.syllable_count(words[0])[0] == 6
            ]
            if single:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="no_double_dactylic_word",
                        offset=lines[SECOND_QUATRAIN.start][0],
                        found="no line of one six-syllable word",
                        expected="one line of the second quatrain to be a single "
                        "double-dactylic word",
                    )
                )
        return self._report(
            good=good,
            total=max(total, 1),
            violations=violations,
            metrics={"lines": float(len(lines)), "estimated_words": float(result.estimated)},
        )
