"""Amphibologia — a phrase that reads two ways because of what the shop sells.

*A Cut Above* over a salon, *Shear Delight*, *Curl Up & Dye*, French *Coup de
foudre* over a coiffeur. Nothing has been displaced and nothing spliced: the
phrase is ordinary and already carries a word of the trade, and the trade is
what makes its second sense audible. That is the third shape of the punning
shopfront, and neither `paronomasia` nor `portmanteau` will look at it —
`paronomasia`'s notes exclude it by name, because it states no relation between
two texts. It states a relation between a text and a trade.

Puttenham lists **"Amphibologia, or the Ambiguous"** in *The Arte of English
Poesie* (1589): speaking "doubtfully, and the sense may be taken two ways". He
lists it among the *vices* of style, beside Pleonasmus and Bomphiologia, which
is a fair place for it: the whole point of the shop sign is that the doubtful
reading is the one you are meant to catch.

**What is actually decided here, and it is less than the figure.** A text
satisfies this row when it carries a word of the declared trade and that word is
genuinely polysemous — it has more than one sense in the lexicon, so there is a
second reading for the trade to activate. `xylophone` has one sense and could
never be ambiguous; `cut` has seventy. What is *not* decided is whether the
phrase is one anybody says, or whether the second reading is funny, or even
whether a reader would notice it. Those are the writer's, as synonymy is the
writer's in `kangaroo_word`.

**Ambiguity is read from `lexicon.glosses`, and that is a committed reading.**
A dictionary's sense count is an editorial decision, not a fact about the
language: Open English WordNet gives `cut` seventy senses and German Wiktionary
gives `Haar` three, and neither number would survive a change of dictionary.
What survives is the ordering — a word with many senses is more ambiguous than
one with a single sense — so the row asks for *at least two* rather than for a
score. `min_senses` is the knob for a caller who wants a stricter reading.

**`apply` selects rather than invents**, and that is not a weaker kind of
generating — it is what this figure is. An amphibologia is not built out of
parts; it is *noticed* in something people already say. So the reader supplies
the phrases, one per line, exactly as ADR 0020 says a corpus reaches this
library, and `apply` hands back the ones that read two ways for the declared
trade. Given fourteen ordinary phrases and a salon, it returns `A Cut Above`,
`Head over heels` and `Curl up with a book`, and leaves `Sheer Delight` behind
because `sheer` is not the trade's word — `shear` is.

The round trip is closed by construction: every line returned was returned
*because* `check` accepted it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from denckring.core import domain as domains
from denckring.core.base import ApplyParams, ConstructiveProcedure
from denckring.core.errors import InvalidParams, MissingCapability, NoCandidateWord
from denckring.core.protocol import Candidate, Evidence, LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans, word_spans


class AmphibologiaParams(BaseModel):
    """Which trade is listening, and how doubtful a word has to be."""

    domain: str | None = Field(
        default=None,
        description=(
            "A shipped trade whose vocabulary makes the second reading: bakery, hair, optician."
        ),
    )
    domain_words: list[str] = Field(
        default_factory=list,
        description="A vocabulary of your own, instead of or alongside a shipped trade.",
    )
    min_senses: int = Field(
        default=2,
        ge=2,
        description=(
            "How many senses the trade word must carry. Two is the floor: with "
            "one there is no second reading for the trade to activate."
        ),
    )

    def trade(self, lang: str) -> frozenset[str]:
        """The vocabulary, casefolded, from both sources.

        Raises `InvalidParams` for an unknown trade, and for *no* trade at all:
        this row is a relation between a text and a trade, so without one there
        is no question to answer. `paronomasia` can fall back on ranking by
        sound alone; there is no equivalent fallback here.
        """
        words = {word.casefold() for word in self.domain_words}
        if self.domain is not None:
            try:
                trade = domains.load(self.domain)
            except KeyError as exc:
                raise InvalidParams("amphibologia", str(exc)) from exc
            words |= {word.casefold() for word in trade.words(lang)}  # type: ignore[arg-type]
        if not words:
            raise InvalidParams(
                "amphibologia",
                "no trade to read the phrase against; pass `domain` or `domain_words`",
            )
        return frozenset(words)


class AmphibologiaApplyParams(AmphibologiaParams, ApplyParams):
    pass


@register
class Amphibologia(ConstructiveProcedure[AmphibologiaParams, AmphibologiaApplyParams]):
    """Constructive by selection: `apply` finds the doubtful phrases in a corpus."""

    id = "amphibologia"

    @classmethod
    def params_model(cls) -> type[AmphibologiaParams]:
        return AmphibologiaParams

    def _check(self, text: str, pack: LanguagePack, params: AmphibologiaParams) -> Report:
        trade = params.trade(pack.lang)
        spans = word_spans(text, pack)
        violations: list[Violation] = []
        evidence: list[Evidence] = []
        carried: list[tuple[int, str, int]] = []

        for offset, word in spans:
            if word.casefold() not in trade:
                continue
            try:
                senses = len(pack.glosses(word))
            except MissingCapability:
                senses = 0
            carried.append((offset, word, senses))

        if not carried:
            violations.append(
                Violation(
                    rule="no_trade_word",
                    offset=None,
                    found=text or "empty text",
                    expected="a phrase carrying a word of the trade",
                )
            )
            return self._report(
                good=0,
                total=1,
                violations=violations,
                metrics={"trade_words": 0.0, "senses": 0.0},
            )

        good = 0
        for offset, word, senses in carried:
            evidence.append(
                Evidence(
                    subject=word,
                    scope="word",
                    offset=offset,
                    value=f"{senses} sense(s) in the lexicon",
                    basis="dictionary",
                )
            )
            if senses >= params.min_senses:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="unambiguous",
                        offset=offset,
                        found=f"{word!r} carries {senses} sense(s)",
                        expected=(
                            f"at least {params.min_senses}, or there is no second "
                            f"reading for the trade to activate"
                        ),
                    )
                )

        return self._report(
            good=good,
            total=len(carried),
            violations=violations,
            metrics={
                "trade_words": float(len(carried)),
                "senses": float(max(senses for _, _, senses in carried)),
            },
            evidence=evidence,
        )

    @classmethod
    def apply_params_model(cls) -> type[AmphibologiaApplyParams]:
        return AmphibologiaApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: AmphibologiaApplyParams) -> Produced:
        """The lines of `text` that read two ways for this trade.

        One candidate per line, never the kept lines joined together: `check`
        judges a phrase, so a candidate has to be a phrase for the round trip to
        mean anything. A joined block would satisfy the checker too — it carries
        the trade words — while being four shop names in a trench coat.

        Ranked by how many senses the trade word carries, most first. That is a
        weak ordering and is meant to be: a sense count is an editor's decision
        (see the module docstring), so it is used to sort and never to decide.
        """
        candidates: list[Candidate] = []
        for _, line in line_spans(text):
            phrase = line.strip()
            if not phrase:
                continue
            report = self.check(
                phrase,
                lang=pack.lang,
                domain=params.domain,
                domain_words=params.domain_words,
                min_senses=params.min_senses,
            )
            if not report.satisfied:
                continue
            candidates.append(Candidate(text=phrase, metrics={"senses": report.metrics["senses"]}))
        if not candidates:
            raise NoCandidateWord(
                self.id,
                "no line of the corpus carries an ambiguous word of this trade",
            )
        candidates.sort(key=lambda c: (-c.metrics["senses"], c.text))
        return Produced(
            candidates=candidates[: params.max_results],
            truncated=len(candidates) > params.max_results,
        )
