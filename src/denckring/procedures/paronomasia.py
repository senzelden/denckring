"""Paronomasia — a phrase displaced by one word that sounds like the one it replaced.

*Bread Pitt* for *Brad Pitt*, *Curl Up & Dye* for *curl up and die*, *Diminu'tif*
for *diminutif*. The figure is old and the salon window is only its most
persistent modern habitat.

The row is `checkability: source`, and what it decides is narrow on purpose.
**Whether a pun is good, or funny, or even a pun at all, is not decided here** —
that is the writer's claim, in the way `kangaroo_word` leaves synonymy to the
writer and `antigram` leaves oppositeness. What is decidable is the *relation*
between two texts the caller declares: that one word of the phrase has been
displaced, that the rest survives untouched so the original stays recoverable,
and that the displacement lands inside a requested band of phonetic distance.

**The band is the constraint, not a score.** A caller asking for
`min_distance=0.0, max_distance=0.0` is asking for a homophone and refuses
anything else; one asking for `0.4` to `0.7` is asking for a pun that has to
work for it, and refuses a homophone as too easy. This is why the band has two
edges rather than being a ceiling: "make it worse" is a writing constraint the
same way "avoid the letter e" is, and a measure that only ever rewarded
closeness could not express it.

**The scope is bounded by what a pronouncing dictionary can answer, and the
bound is narrower than the figure.** A displacement is checkable only when the
word that lands is itself in the dictionary. The blends and compound splices
that dominate real punning shop names put a *coined* word there — `Hairitage`,
`Haarmonie`, `Hairways`, `Barberella`, `Chaarisma`, `atmosph'air` — and no pack
here can pronounce a word it has never seen; all six of those raise
`MissingCapability`, measured rather than assumed. That family is `portmanteau`, which is
a row of its own — and it needed no grapheme-to-phoneme model in the end. This
docstring named `phonemes.g2p` as the blocker, in good faith, and the measurement
in ADR 0042 overturned it: a blend splices two words the dictionary already has,
so the coinage is checked as a derived form rather than pronounced. Reading
`describe_procedure("paronomasia")` and concluding *this* row checks *Haarmonie*
would still be a mistake — it is the next row along that does.

An unresolvable word is reported, never guessed at. `unknown_word` carries the
same three readings as `n_plus_7.ambiguous_nouns` and `RhymeParams.unknown_rhyme`,
and the default reports. Scoring it as a violation rather than dropping it is
`spoonerism`'s ruling R14: a displaced pair has nothing to fall back on, and
dropping it would let a text of nothing but coinages score 1.0 vacuously.

The distance itself is `core.phonetics.phoneme_distance`, whose docstring
records which reading of "phonetic distance" it commits to and what that reading
cannot see.
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from denckring.core import domain as domains
from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.errors import InvalidParams, MissingCapability, NoCandidateWord
from denckring.core.phonetics import (
    bare_phonemes,
    cannot_be_within,
    distance_prepared,
    phoneme_distance,
    prepared,
    symbol_counts,
)
from denckring.core.protocol import Candidate, Evidence, LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import word_spans


def _pronounce(word: str, pack: LanguagePack) -> list[str] | None:
    """The word's phonemes without stress marks, or `None` if unpronounceable.

    Catches `MissingCapability` around the per-word lookup only, never the
    surrounding check, so one coinage cannot take an exception past the row
    that exists to report on it — `spoonerism._onset_or_none` does the same for
    the same reason.
    """
    try:
        return bare_phonemes(pack.phonemes(word))
    except MissingCapability:
        return None


#: Built lexicons, keyed by which pack answered. Not an `lru_cache` on the pack
#: itself: `LanguagePack` is a `Protocol`, and a protocol is not `Hashable` to a
#: strict type checker however hashable the concrete packs happen to be. The
#: language alone would be the wrong key — `de` resolves to any of four pack
#: classes depending on which data distributions are installed, and they do not
#: all pronounce the same words.
_LEXICONS: dict[tuple[str, str], tuple[tuple[str, list[str], int, Counter[str]], ...]] = {}


def _pronounceable_lexicon(
    pack: LanguagePack,
) -> tuple[tuple[str, list[str], int, Counter[str]], ...]:
    """Every graded word this pack can also pronounce, with its band.

    Cached, because building it walks the whole lexicon: measured at 0.3s for
    English and 1.2s for German, which is affordable once and not affordable
    once per call in a fuzz run of six hundred.

    The two lists do not cover each other. Measured: 45,884 of English's 77,078
    graded words are in CMUdict, and 72,734 of German's 101,296 are in the
    Wiktionary pronunciations; French's 125,343 are all in Lexique, because
    both halves come from the same source there. A word missing from either is
    simply not a candidate — the generator can only offer displacements its own
    checker will then resolve.
    """
    key = (pack.lang, type(pack).__name__)
    cached = _LEXICONS.get(key)
    if cached is not None:
        return cached
    entries: list[tuple[str, list[str], int, Counter[str]]] = []
    for word, band in pack.graded_words().items():
        phonemes = _pronounce(word, pack)
        if phonemes:
            # Normalised here, once, rather than on every comparison: see
            # `phonetics.prepared`.
            ready = prepared(phonemes, pack.lang)
            entries.append((word, ready, band, symbol_counts(ready)))
    built = tuple(entries)
    _LEXICONS[key] = built
    return built


def _is_inflection(displaced: str, landed: str) -> bool:
    """Whether one word is just the front of the other.

    `Rolling` and `Roll`, `eyes` and `eye`, `lens` and `lenses`: a displacement
    onto a word that only adds or drops an ending is morphology wearing a pun's
    clothes, and the checker cannot tell the difference because a plural
    genuinely is a different word at a small phonetic distance. The generator
    can at least stop *offering* it first.

    Deliberately a prefix test and not a stemmer. The pairs this row exists for
    are untouched by it — `die`/`dye`, `Brad`/`Bread`, `Life`/`Loaf`,
    `Sheer`/`Shear`, `Site`/`Sight` — because a real sound-pun changes something
    inside the word, not only what hangs off the end. A stemmer would start
    making claims about morphology that this project has no data to support.
    """
    a, b = displaced.casefold(), landed.casefold()
    if a == b:
        return False
    return a.startswith(b) or b.startswith(a)


def _match_case(source: str, replacement: str) -> str:
    """The replacement wearing the displaced word's capitalisation.

    Only the leading capital is carried, which is the case distinction that
    exists in all three languages — German capitalises every common noun, so a
    displacement into lower case there is not a stylistic quibble but a
    misspelling. `check` is indifferent either way; this is for the reader.
    """
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


class ParonomasiaParams(SourceParams):
    """The declared phrase, the band, and how much may be displaced."""

    min_distance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="The closest a displacement may sound to the word it replaces.",
    )
    max_distance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="The furthest a displacement may sound from the word it replaces.",
    )
    max_displacements: int = Field(
        default=1,
        ge=1,
        description=(
            "How many words of the phrase may be displaced. Above one, the "
            "original grows harder to hear behind the pun."
        ),
    )
    unknown_word: Literal["undecidable", "free", "strict"] = Field(
        default="undecidable",
        description=(
            "How to read a word absent from the pronouncing dictionary: report "
            "it, accept it unchecked, or refuse it."
        ),
    )

    @model_validator(mode="after")
    def _band_must_be_an_interval(self) -> ParonomasiaParams:
        if self.min_distance > self.max_distance:
            raise InvalidParams(
                "paronomasia",
                f"min_distance {self.min_distance} is above max_distance "
                f"{self.max_distance}; the band would be empty",
            )
        return self


class ParonomasiaApplyParams(ParonomasiaParams, ApplyParams):
    """The check's params, plus which trade's sign the pun is going on."""

    domain: str | None = Field(
        default=None,
        description=(
            "A trade whose vocabulary should win: bakery, hair, optician. Its "
            "words are offered before any others at the same distance."
        ),
    )
    domain_words: list[str] = Field(
        default_factory=list,
        description=(
            "A vocabulary of your own, ranked the same way. Use instead of "
            "`domain`, or alongside it to extend a shipped trade."
        ),
    )

    domain_only: bool = Field(
        default=False,
        description=(
            "Offer only words of the trade, instead of ranking them first. For a "
            "caller who wants a shop sign and nothing else."
        ),
    )

    def trade(self, lang: str) -> dict[str, str]:
        """The vocabulary that wins: casefolded key, and how the trade spells it.

        The spelling is carried, not just the membership, because the lexicon
        cannot always be trusted for it. German's graded words come from a
        frequency corpus that is **entirely lower case** — `graded_words()["haar"]`
        is 10 and `"Haar"` is absent — so a displacement taken from it and
        rendered as the lexicon spells it puts `Alles haar` on the sign, which is
        a misspelling in a language that capitalises every noun. `rules/german.md`
        records the same trap on the input side: decide about case *before*
        intersecting. The domain files are authored, so they spell their own
        nouns correctly, and that is the spelling the sign gets.

        Raises `InvalidParams` for an unknown trade rather than letting the
        loader's `KeyError` escape: to this row a domain is a parameter value,
        so a wrong one is a wrong argument and not a missing file. A trade that
        ships nothing in this language is not an error — `optician` has only
        English, deliberately — it simply contributes no words, and the search
        falls back to ranking by sound alone.
        """
        words = {word.casefold(): word for word in self.domain_words}
        if self.domain is not None:
            try:
                trade = domains.load(self.domain)
            except KeyError as exc:
                raise InvalidParams("paronomasia", str(exc)) from exc
            for word in trade.words(lang):  # type: ignore[arg-type]
                words.setdefault(word.casefold(), word)
        return words


@register
class Paronomasia(ConstructiveProcedure[ParonomasiaParams, ParonomasiaApplyParams]):
    """Constructive: `apply` performs the displacement `check` verifies."""

    id = "paronomasia"

    @classmethod
    def params_model(cls) -> type[ParonomasiaParams]:
        return ParonomasiaParams

    def _check(self, text: str, pack: LanguagePack, params: ParonomasiaParams) -> Report:
        spans = word_spans(text, pack)
        source_spans = word_spans(params.source, pack)
        if len(spans) != len(source_spans):
            return self._report(
                good=0,
                total=1,
                violations=[
                    Violation(
                        rule="length_mismatch",
                        offset=None,
                        found=f"{len(spans)} word(s)",
                        expected=f"{len(source_spans)}, as in the declared phrase",
                    )
                ],
                metrics={"displacements": 0.0, "unresolved": 0.0},
            )

        violations: list[Violation] = []
        good = 0
        distances: list[float] = []
        evidence: list[Evidence] = []
        unresolved = 0
        displaced = 0

        for (offset, word), (_, original) in zip(spans, source_spans, strict=True):
            if word.casefold() == original.casefold():
                good += 1
                continue
            displaced += 1
            here = _pronounce(word, pack)
            there = _pronounce(original, pack)
            if here is None or there is None:
                unresolved += 1
                if params.unknown_word == "free":
                    good += 1
                    continue
                violations.append(
                    Violation(
                        rule="unresolvable_pronunciation",
                        offset=offset,
                        found=f"{word!r} for {original!r}",
                        expected="both words in the pronouncing dictionary",
                        note=(
                            None
                            if params.unknown_word == "strict"
                            else "undecidable here; pass unknown_word to settle it"
                        ),
                    )
                )
                continue
            distance = phoneme_distance(here, there, pack.lang)
            distances.append(distance)
            evidence.append(
                Evidence(
                    subject=word,
                    scope="word",
                    offset=offset,
                    value=f"{' '.join(here)} for {' '.join(there)} at {distance:.3f}",
                    basis="dictionary",
                )
            )
            if not params.min_distance <= distance <= params.max_distance:
                violations.append(
                    Violation(
                        rule="distance_out_of_band",
                        offset=offset,
                        found=f"{word!r} for {original!r} at {distance:.3f}",
                        expected=f"between {params.min_distance} and {params.max_distance}",
                    )
                )
                continue
            good += 1

        total = len(spans)
        if displaced == 0:
            violations.append(
                Violation(
                    rule="no_displacement",
                    offset=None,
                    found="the phrase unchanged",
                    expected="one word displaced by another close to it in sound",
                )
            )
            good = 0
            total = max(total, 1)
        elif displaced > params.max_displacements:
            violations.append(
                Violation(
                    rule="unrecoverable",
                    offset=None,
                    found=f"{displaced} words displaced",
                    expected=f"at most {params.max_displacements}",
                )
            )
            good = min(good, total - 1)

        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "displacements": float(displaced),
                "unresolved": float(unresolved),
                "max_distance": max(distances, default=0.0),
                "mean_distance": (sum(distances) / len(distances)) if distances else 0.0,
            },
            evidence=evidence,
        )

    @classmethod
    def apply_params_model(cls) -> type[ParonomasiaApplyParams]:
        return ParonomasiaApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: ParonomasiaApplyParams) -> Produced:
        """Displace one word of `text` by every lexicon word inside the band.

        `text` is the phrase, and `params.source` is the same string — the spine
        injects it (`core/base.py:317-338`), which is what makes the produced
        text checkable against what it was made from without the caller
        repeating themselves.

        Exactly one word is displaced however high `max_displacements` is set.
        The parameter bounds what `check` will *accept*; stacking displacements
        here would multiply the search by the phrase length for candidates a
        reader cannot hear the original behind anyway.

        Substitution is by span offset rather than by re-joining tokens, so
        punctuation, spacing and anything the tokeniser does not call a word
        survive untouched — `n_plus_7.displace` says why: a generator that
        normalised the whitespace would produce text its own checker then
        rejected for the wrong reason.

        Candidates are prefiltered on phoneme length and on sharing a first or
        last phoneme before any distance is computed. Measured on English: this
        takes 45,884 pronounceable words down to between 143 and 2,424 per
        position, and the whole scan then runs in under a hundredth of a second
        — which is why there is no search budget here in the way `anagram` and
        `word_ladder` need one. The prefilter is not a heuristic standing in for
        the band; every survivor is still measured, and the band decides.
        """
        spans = word_spans(text, pack)
        trade = params.trade(pack.lang)
        lexicon = _pronounceable_lexicon(pack)
        if params.domain_only and trade:
            # The whole lexicon is the wrong haystack when the caller has already
            # said which twenty words they want. Scanning it anyway is what made a
            # street of eight shopfronts cost nineteen seconds to draw; restricted
            # to the trade it is immediate, and the answer is identical because
            # `in_trade` already leads the ranking — this changes what is
            # *searched*, never what wins.
            lexicon = tuple(entry for entry in lexicon if entry[0].casefold() in trade)
        found: list[Candidate] = []

        for offset, word in spans:
            raw = _pronounce(word, pack)
            if raw is None:
                continue
            target = prepared(raw, pack.lang)
            folded = word.casefold()
            target_counts = symbol_counts(target)
            for candidate, phonemes, band, counts in lexicon:
                if candidate.casefold() == folded:
                    continue
                if cannot_be_within(phonemes, target, params.max_distance, counts, target_counts):
                    continue
                # `ceiling` lets the measure abandon a candidate that has
                # already lost, which is what makes an honest prefilter
                # affordable — see `phonetics._levenshtein`.
                distance = distance_prepared(phonemes, target, ceiling=params.max_distance)
                if not params.min_distance <= distance <= params.max_distance:
                    continue
                # The trade spells its own words — this is what keeps a German
                # noun capitalised when the lower-case frequency list is where the
                # candidate came from. The displaced word's own case is then applied
                # on top, so `Brad` -> `Bread` keeps its capital and `klar` -> `Haar`
                # keeps the one the noun is entitled to either way.
                authored = trade.get(candidate.casefold(), candidate)
                replacement = _match_case(word, authored)
                found.append(
                    Candidate(
                        text=text[:offset] + replacement + text[offset + len(word) :],
                        metrics={
                            "distance": distance,
                            "band": float(band),
                            "in_trade": float(candidate.casefold() in trade),
                            "inflection": float(_is_inflection(word, candidate)),
                        },
                    )
                )

        if not found:
            raise NoCandidateWord(
                self.id,
                "no word in the lexicon displaces any word of this phrase "
                "inside the requested band",
            )

        # The trade first, then closest in sound, then commonest, then alphabetically.
        #
        # The order matters more than it looks, and an earlier version had it wrong.
        # Ranking by commonness first made the key lexicographic in the wrong
        # place: `bread` is SCOWL band 20 and `brand`, `bad`, `it` and `put` are
        # all band 10, so every one of them outranked `bread` *whatever* the
        # distance, and `Bread Pitt` came back 74th behind `Brad It`. Band 10 and
        # band 20 are both words any reader knows, so commonness was not buying
        # what its comment claimed; it was only drowning out the measure this row
        # is about. It now breaks ties and nothing more.
        #
        # `in_trade` leads because a pun's subject is what the shop sells: at equal
        # distance, `bread` for a bakery beats `brand` for nothing. With no domain
        # given every candidate scores 0 there and the key falls through to sound,
        # which is the general behaviour and still the right one.
        # Trade first, then closest in sound, then *not an inflection*, then
        # commonest, then alphabetically.
        #
        # `inflection` earns its place ahead of `band` on a measured case:
        # `Rolling Stones` for a bakery offers `Roll Stones` and `Rolling Scone`
        # at exactly the same distance of 0.400, and commonness preferred
        # `roll` (SCOWL band 10) over `scone` (band 50) — so the row that
        # catalogues the figure returned the one where nothing had really
        # happened. `Rolling` to `Roll` drops an ending; `Stones` to `Scone`
        # is the joke.
        found.sort(
            key=lambda c: (
                -c.metrics["in_trade"],
                c.metrics["distance"],
                c.metrics["inflection"],
                c.metrics["band"],
                c.text,
            )
        )
        return Produced(
            candidates=found[: params.max_results],
            truncated=len(found) > params.max_results,
        )
