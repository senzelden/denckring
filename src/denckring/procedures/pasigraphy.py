"""Pasigraphy — a sentence sent through a numbered vocabulary."""

from __future__ import annotations

from pydantic import Field

from denckring.core import pasigraph
from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams, plain
from denckring.core.protocol import LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans

#: Stands in the rendering where a word could not cross, so the gap is visible
#: in the output rather than silently closed.
GAP = "—"


class PasigraphyParams(SourceParams):
    table: str = Field(description="The numbered vocabulary, as JSON.")
    from_language: str = Field(description="Language the source is written in.")
    to_language: str = Field(description="Language the rendering is in.")
    require_complete: bool = Field(
        default=False,
        description="Every word must cross; a gap in the rendering is a failure.",
    )


class PasigraphyApplyParams(PasigraphyParams, ApplyParams):
    pass


def render(
    source: str, pack: LanguagePack, table: pasigraph.Table, sender: str, receiver: str
) -> tuple[list[str], list[str], list[str]]:
    """Send each word through its number, keeping a record of what was lost."""
    produced: list[str] = []
    unnumbered: list[str] = []
    stranded: list[str] = []
    for _, word in word_spans(source, pack):
        number = table.number_for(word, sender)
        if number is None:
            unnumbered.append(word)
            produced.append(GAP)
            continue
        target = table.word_at(number, receiver)
        if target is None:
            stranded.append(f"{word} ({number})")
            produced.append(GAP)
            continue
        produced.append(target)
    return produced, unnumbered, stranded


@register
class Pasigraphy(ConstructiveProcedure[PasigraphyParams, PasigraphyApplyParams]):
    """Kircher's universal writing, and the losses it takes on the way.

    A word becomes a number and the number becomes a word again in another
    language. The checker verifies the rendering against the table — and counts
    what the crossing cost: words with no number, numbers with no entry at the
    far end, and numbers carrying more than one word, where two distinct things
    arrive as one.

    No vocabulary ships. Kircher's own has not been transcribed into anything
    this project could verify, and a checker measuring against an invented table
    would be measuring nothing.
    """

    id = "pasigraphy"

    @classmethod
    def params_model(cls) -> type[PasigraphyParams]:
        return PasigraphyParams

    def _check(self, text: str, pack: LanguagePack, params: PasigraphyParams) -> Report:
        table = pasigraph.parse(params.table)
        expected, unnumbered, stranded = render(
            params.source, pack, table, params.from_language, params.to_language
        )
        produced = [word for _, word in word_spans(text, pack)]
        # The gap marker is not a word, so it will not be tokenised; compare on
        # the words that did cross.
        got = [word for word in produced]

        violations: list[Violation] = []
        matched = 0
        wanted = [word for word in expected if word != GAP]
        for index, word in enumerate(wanted):
            if index < len(got) and got[index].casefold() == word.casefold():
                matched += 1
            else:
                violations.append(
                    Violation(
                        rule="wrong_rendering",
                        offset=None,
                        found=got[index] if index < len(got) else "",
                        expected=word,
                    )
                )
        if len(got) > len(wanted):
            violations.append(
                Violation(
                    rule="extra_words",
                    offset=None,
                    found=" ".join(got[len(wanted) :]),
                    expected="",
                )
            )
        # A rendering that shows its gaps is still the rendering the table
        # produces. The losses are counted either way; they only fail the check
        # when the caller asked for a complete crossing.
        if params.require_complete:
            for word in unnumbered:
                violations.append(
                    Violation(
                        rule="no_number_for_word",
                        offset=None,
                        found=word,
                        expected=f"a word the table numbers in {params.from_language!r}",
                        note="the vocabulary cannot carry this word at all",
                    )
                )
            for entry in stranded:
                violations.append(
                    Violation(
                        rule="no_word_at_number",
                        offset=None,
                        found=entry,
                        expected=f"an entry for {params.to_language!r} at that number",
                        note="the number crossed but arrived at nothing",
                    )
                )

        collisions = table.collisions(params.to_language)
        total = max(len(wanted), len(got), 1) + (
            len(unnumbered) + len(stranded) if params.require_complete else 0
        )
        return self._report(
            good=max(total - len(violations), 0),
            total=total,
            violations=violations,
            metrics={
                "words": float(len(produced)),
                "unnumbered": float(len(unnumbered)),
                "stranded": float(len(stranded)),
                "colliding_numbers": float(len(collisions)),
            },
        )

    @classmethod
    def apply_params_model(cls) -> type[PasigraphyApplyParams]:
        return PasigraphyApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: PasigraphyApplyParams) -> Produced:
        """Send `text` across, marking every place a word could not follow."""
        table = pasigraph.parse(params.table)
        produced, _, _ = render(text, pack, table, params.from_language, params.to_language)
        return plain([" ".join(produced)])
