"""Ghazal — couplets closing on a repeated word, the radif, with a rhyme before it.

The radif is taken from the opening couplet rather than given as a parameter: the
form defines it as whatever word the first couplet repeats, so asking the caller
would let a text declare its own compliance.

A ghazal is radif *and* qafia: the repeated end word, and a rhyme immediately
preceding it. The word before the radif in line 1 sets the qafia; every later
line carrying the radif must rhyme with it there. Scored as one more check per
carrying line rather than a hard gate — real ghazals vary in how strictly the
qafia is kept, so a poem that drops it does not fail outright, it scores lower.
"""

from __future__ import annotations

from denckring.core.base import BaseProcedure, RhymeParams
from denckring.core.prosody import word_rhyme_keys
from denckring.core.protocol import Evidence, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class GhazalParams(RhymeParams):
    pass


@register
class Ghazal(BaseProcedure[GhazalParams]):
    """Every second line ends on the word both lines of the first couplet end on."""

    id = "ghazal"

    @classmethod
    def params_model(cls) -> type[GhazalParams]:
        return GhazalParams

    def _check(self, text: str, pack: LanguagePack, params: GhazalParams) -> Report:
        lines = [line for _, line in line_spans(text)]
        violations: list[Violation] = []
        if len(lines) < 2:
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="wrong_line_count",
                        offset=None,
                        found=f"{len(lines)} lines",
                        expected="at least 2 lines",
                    )
                ],
                metrics={"couplets": 0.0},
            )

        def words_of(line: str) -> list[str]:
            return [word.casefold() for _, word in word_spans(line, pack)]

        first_words = words_of(lines[0])
        radif = first_words[-1] if first_words else ""
        base_qafia, base_exact = (
            word_rhyme_keys(first_words[-2], pack)
            if len(first_words) >= 2
            else (frozenset[str](), False)
        )

        good = 0
        total = 0
        qafia_good = 0
        qafia_total = 0
        estimated = 0
        # The qafia is the word *before* the radif, so the account has to name
        # that word and not the line ending: reporting the radif would describe
        # the one word every carrying line is required to share.
        evidence: list[Evidence] = []
        # The opening couplet carries the radif on both lines; thereafter every second.
        carriers = [1, *range(3, len(lines), 2)]
        for index in carriers:
            total += 1
            words = words_of(lines[index])
            actual = words[-1] if words else ""
            if actual == radif:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="missing_radif",
                        offset=None,
                        found=actual,
                        expected=radif,
                    )
                )
                continue
            if len(first_words) < 2 or len(words) < 2:
                continue
            candidate, candidate_exact = word_rhyme_keys(words[-2], pack)
            evidence.append(
                Evidence(
                    subject=words[-2],
                    value="/".join(sorted(candidate)) if candidate else "no rhyme key",
                    basis="dictionary" if candidate_exact else "estimated",
                )
            )
            if not (base_exact and candidate_exact):
                # The dictionary does not carry one of the pair, so this couplet
                # cannot be judged. What that means is the caller's decision.
                if params.unknown_rhyme == "undecidable":
                    estimated += 1
                    continue
                qafia_total += 1
                if params.unknown_rhyme == "free":
                    qafia_good += 1
                else:
                    violations.append(
                        Violation(
                            rule="unknown_rhyme",
                            offset=None,
                            found=words[-2] if not candidate_exact else first_words[-2],
                            expected="a word the pronouncing dictionary carries",
                        )
                    )
                continue
            qafia_total += 1
            if candidate & base_qafia:
                qafia_good += 1
            else:
                violations.append(
                    Violation(
                        rule="broken_qafia",
                        offset=None,
                        found=words[-2],
                        expected=f"a rhyme for {first_words[-2]!r}",
                    )
                )
        return self._report(
            good=good + qafia_good,
            total=max(total + qafia_total, 1),
            violations=violations,
            metrics={
                "couplets": float(len(lines) // 2),
                "estimated_words": float(estimated),
            },
            evidence=evidence,
        )
