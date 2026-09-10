"""Portmanteau — a coinage that carries one word inside another.

*Haarmonie* is *Harmonie* with `Haar` showing through it; *Hairitage* is
*heritage* with `hair`; *Föhnix* is *Phönix* with `Föhn`. This is the half of
the punning-shopfront tradition `paronomasia` cannot reach, because the surface
is a word no pronouncing dictionary carries.

**It turns out not to need a grapheme-to-phoneme model, and that is the whole
idea of this row.** A blend is never an arbitrary string: the host word and the
word spliced into it are both ordinary dictionary entries. So the coinage is
verified as a *derived form* — the host is still recoverable behind it, the
spliced word is really there, and that word sounds like a stretch of the host it
covers — and nothing unknown is ever sounded out. `phonemes.g2p` was named on
`paronomasia` as what this family was blocked on; the measurement said otherwise.

**The one approximation, stated because it is the row's weakest joint.** Deciding
*which* phonemes of the host the spliced letters cover would need grapheme-to-
phoneme alignment, which this project does not have. Instead the check asks
whether the spliced word sounds like **some** window of the host's pronunciation
of about the right length. That is weaker: it would accept a blend whose word
matches a stretch of the host somewhere other than where it was actually spliced.
It is not weaker in a way that lets nonsense through — the word must still be
present in the coinage, be a real word, and leave the host recoverable — and it
is the strongest reading available without an aligner.

**What the row still cannot reach**, both measured rather than assumed:

- a host the lexicon does not carry, which for shop names is usually a proper
  noun — `Barbarella` is absent from CMUdict, so `Barberella` is undecidable;
- the cross-lingual blend — French `Atmosph'air`, German `British Hairways` —
  which needs `phonemes.bilingual`, the same capability `homophonic_translation`
  is blocked on and which no pack provides.

**`apply` generates by proposing splices and letting `check` dispose**, which is
this project's own thesis turned into a search. Knowing *where* to splice would
need the grapheme-to-phoneme alignment named above; so it is not decided. Every
way of putting each trade word into the host is proposed — replace any stretch,
including none — and the checker throws out everything that is not a blend. What
survives is ranked closest-sounding first.

Measured against the attested corpus in `docs/research/`, with the shipped hair
vocabulary: **the real name comes back first for 10 of 12 hosts** and is in the
first ten for 11. The two it misses are recorded in ADR 0043 rather than tuned
away, because twelve examples is not enough to tune against — `Chamäleon` gives
`ChKammäleon` ahead of `Kammäleon` at rank 23, a seam stutter that keeps more of
the host and therefore wins on recoverability. Three fixes were tried and each
made the whole result worse; they are named in the ADR so nobody spends the
afternoon again.
"""

from __future__ import annotations

import unicodedata
from typing import Literal

from pydantic import Field, model_validator

from denckring.core import domain as domains
from denckring.core.base import ApplyParams, ConstructiveProcedure, SourceParams
from denckring.core.errors import InvalidParams, MissingCapability, NoCandidateWord
from denckring.core.phonetics import across_languages, bare_phonemes, phoneme_distance
from denckring.core.protocol import (
    Candidate,
    Evidence,
    Lang,
    LanguagePack,
    Produced,
    Report,
    Violation,
)
from denckring.core.registry import register
from denckring.core.text import word_spans
from denckring.lang import get_pack

#: How far a window may run from the spliced word's own length. One phoneme
#: either side: a splice that covers a stretch two phonemes longer or shorter
#: than itself is not covering it, it is sitting next to it.
_WINDOW_SLACK = 1


def _pronounce(text: str, pack: LanguagePack) -> list[str] | None:
    """The phonemes of a word **or a phrase**, or `None` if any of it is unknown.

    A host is often more than one word — `Mona Lisa` behind *Monhaarlisa*, `Hart
    am Limit` behind *Haart am Limit* — and `pack.phonemes` answers about a word.
    Each word is looked up and the results run together, which is the right
    reading here: the splice covers a stretch of the *sound of the whole host*,
    and where a word boundary falls inside that stretch is exactly what a blend
    ignores.

    All-or-nothing on purpose. One unknown word in a three-word host would
    otherwise silently shorten the pronunciation and move every distance
    computed from it, which is worse than saying so.
    """
    words = [word for _, word in word_spans(text, pack)] or [text]
    out: list[str] = []
    for word in words:
        try:
            out.extend(bare_phonemes(pack.phonemes(word)))
        except MissingCapability:
            return None
    return out


def _closest_window(
    host: list[str], splice: list[str], lang: str, splice_lang: str | None = None
) -> tuple[float, int, int]:
    """The stretch of `host` that `splice` sounds most like: `(distance, at, length)`.

    Searched rather than aligned — see the module docstring for why, and for what
    that costs. Lengths within `_WINDOW_SLACK` of the spliced word's own are
    tried at every offset; the best is returned.

    With `splice_lang`, the two sides come from different packs and are compared
    through IPA with the rhotics folded — see `phonetics.across_languages`. That
    is the whole of what made the commonest French salon name unreachable: the
    English `hair` and the French `air` in `imaginaire` are one edit apart once
    they are written in the same alphabet, and incomparable before.
    """
    # Seeded from a real window rather than from `(1.0, 0, 0)`. That initial
    # value was itself a bug: when no window scored below 1.0 it survived to the
    # end and the row reported a *zero-length* window as its evidence — `h aː ɐ̯
    # for  at 1.000`, a comparison against nothing, which read as a loose match
    # and was no match at all. Two shipped blends were resting on it.
    best = (1.0, 0, len(host))
    wanted = len(splice)
    for length in range(max(1, wanted - _WINDOW_SLACK), wanted + _WINDOW_SLACK + 1):
        for start in range(0, max(1, len(host) - length + 1)):
            window = host[start : start + length]
            if not window:
                continue
            distance = (
                across_languages(window, lang, splice, splice_lang)
                if splice_lang is not None and splice_lang != lang
                else phoneme_distance(window, splice, lang)
            )
            if distance < best[0]:
                best = (distance, start, length)
    return best


def _orthographic_distance(a: str, b: str) -> float:
    """Normalised letter-level edit distance, for "is the host still there".

    Spelling, not sound, and on purpose: recoverability is about whether a reader
    seeing the sign can still read the phrase behind it, which is a question
    about the letters in front of them. `paronomasia` asks the same question by
    counting displaced words; a blend happens inside one word, so it is counted
    in letters instead.
    """
    left, right = a.casefold(), b.casefold()
    longest = max(len(left), len(right))
    if longest == 0:
        return 0.0
    previous = list(range(len(right) + 1))
    for i, x in enumerate(left, start=1):
        current = [i]
        for j, y in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1] / longest


class PortmanteauParams(SourceParams):
    """The host word, the word spliced into it, and how far each may travel."""

    splice: str = Field(description="The word made visible inside the coinage.")
    min_distance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="The closest the spliced word may sound to the stretch it covers.",
    )
    max_distance: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="The furthest the spliced word may sound from the stretch it covers.",
    )
    splice_lang: Lang | None = Field(
        default=None,
        description=(
            "The language the spliced word belongs to, when it is not the host's. "
            "`Imagin'hair` is English inside French."
        ),
    )
    max_host_distance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "How far the coinage may travel from its host in spelling before the "
            "host stops being recoverable behind it."
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
    def _band_must_be_an_interval(self) -> PortmanteauParams:
        if self.min_distance > self.max_distance:
            raise InvalidParams(
                "portmanteau",
                f"min_distance {self.min_distance} is above max_distance "
                f"{self.max_distance}; the band would be empty",
            )
        return self


def _bare_letters(text: str) -> str:
    """Letters and digits only, accents stripped, casefolded.

    Splices are compared in this form because the coinages the tradition
    actually produces add punctuation and change case at the seam — `Diminu'tif`
    for `diminutif`, `A-Tif-Fé` for `attifé`, `Chaarisma` for `Charisma`. An
    earlier measurement compared the raw strings and concluded that only 12 of 39
    attested blends were a clean single splice; normalised, it is 38 of 39. The
    conclusion was about the probe, not the data.
    """
    kept = "".join(ch for ch in text if ch.isalnum() or ch.isspace())
    decomposed = unicodedata.normalize("NFD", kept)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def _seam(host: str, start: int, end: int, splice: str) -> float:
    """How much the stretch being replaced already resembled the splice.

    A real blend swaps a chunk for something like it — `Har` becomes `Haar` —
    where the junk this search produces mostly *inserts* beside a chunk it keeps,
    giving `HHaarmonie`. Used to rank and deliberately **not** to filter:
    measured over the attested names, a bound tight enough to help would lose
    `Coiff'Hair`, which replaces `ure` with `hair` and resembles it not at all.
    """
    return _orthographic_distance(host[start:end], splice)


class PortmanteauApplyParams(SourceParams, ApplyParams):
    """What the generator needs, which is not what the check needs.

    Deliberately not a subclass of `PortmanteauParams`: that model requires
    `splice`, and the splice is the thing being generated. A caller who already
    knew which word to put in would not be asking.
    """

    domain: str | None = Field(
        default=None,
        description="A trade whose vocabulary to splice from: bakery, hair, optician.",
    )
    domain_words: list[str] = Field(
        default_factory=list,
        description="A vocabulary of your own to splice from.",
    )
    max_distance: float = Field(default=0.7, ge=0.0, le=1.0)
    max_host_distance: float = Field(default=0.5, ge=0.0, le=1.0)
    splice_lang: Lang | None = Field(default=None)

    def trade(self, lang: str) -> tuple[str, ...]:
        """The vocabulary to splice from, in the order it was written."""
        words = list(self.domain_words)
        if self.domain is not None:
            try:
                trade = domains.load(self.domain)
            except KeyError as exc:
                raise InvalidParams("portmanteau", str(exc)) from exc
            words.extend(trade.words(self.splice_lang or lang))  # type: ignore[arg-type]
        return tuple(dict.fromkeys(words))


@register
class Portmanteau(ConstructiveProcedure[PortmanteauParams, PortmanteauApplyParams]):
    """Constructive: `apply` proposes splices and `check` disposes of them."""

    id = "portmanteau"

    @classmethod
    def params_model(cls) -> type[PortmanteauParams]:
        return PortmanteauParams

    def _check(self, text: str, pack: LanguagePack, params: PortmanteauParams) -> Report:
        coinage = text.strip()
        splice, host = params.splice.strip(), params.source.strip()
        violations: list[Violation] = []
        evidence: list[Evidence] = []
        checks = 3
        good = 0

        # 1. The word is actually visible in the coinage.
        if splice and splice.casefold() in coinage.casefold():
            good += 1
        else:
            violations.append(
                Violation(
                    rule="splice_not_present",
                    offset=None,
                    found=coinage or "empty text",
                    expected=f"a coinage containing {splice!r}",
                )
            )

        # 2. The host is still recoverable behind it — and is not simply it.
        host_distance = _orthographic_distance(coinage, host)
        if coinage and host and coinage.casefold() == host.casefold():
            # `Crustacean` really does contain `crust`, and `Sightseeing`
            # contains `sight`, and both sailed through an earlier draft at a
            # spelling distance of 0.000 — because nothing had been spliced at
            # all. A word that already carries another inside it is the *found*
            # pun, which `paronomasia`'s own notes exclude for the same reason:
            # it states no relation between two texts, it is one text.
            violations.append(
                Violation(
                    rule="identical_to_host",
                    offset=None,
                    found=coinage,
                    expected="a coinage, not the host word itself",
                )
            )
        elif host_distance <= params.max_host_distance:
            good += 1
        else:
            violations.append(
                Violation(
                    rule="host_unrecoverable",
                    offset=None,
                    found=f"{coinage!r} is {host_distance:.3f} from {host!r} in spelling",
                    expected=f"at most {params.max_host_distance}",
                )
            )

        # 3. The spliced word sounds like a stretch of the host.
        # A cross-lingual splice is resolved in its own pack. `Imagin'hair` is
        # English inside French, and the French lexicon neither knows `hair` nor
        # can pronounce it — asking it to would be asking the wrong dictionary.
        splice_pack = get_pack(params.splice_lang) if params.splice_lang else pack
        splice_phonemes = _pronounce(splice, splice_pack) if splice else None
        host_phonemes = _pronounce(host, pack) if host else None
        distance = 0.0
        if splice and not splice_pack.is_word(splice):
            violations.append(
                Violation(
                    rule="splice_not_a_word",
                    offset=None,
                    found=splice,
                    expected="a word the lexicon knows, not an arbitrary run of letters",
                )
            )
        elif splice_phonemes is None or host_phonemes is None:
            if params.unknown_word == "free":
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="unresolvable_pronunciation",
                        offset=None,
                        found=f"{splice!r} in {host!r}",
                        expected="both words in the pronouncing dictionary",
                        note=(
                            None
                            if params.unknown_word == "strict"
                            else "undecidable here; pass unknown_word to settle it"
                        ),
                    )
                )
        else:
            distance, at, length = _closest_window(
                host_phonemes, splice_phonemes, pack.lang, params.splice_lang
            )
            evidence.append(
                Evidence(
                    subject=splice,
                    scope="word",
                    offset=None,
                    value=(
                        f"{' '.join(splice_phonemes)} for "
                        f"{' '.join(host_phonemes[at : at + length])} at {distance:.3f}"
                    ),
                    basis="dictionary",
                )
            )
            if params.min_distance <= distance <= params.max_distance:
                good += 1
            else:
                violations.append(
                    Violation(
                        rule="sound_out_of_band",
                        offset=None,
                        found=f"{splice!r} is {distance:.3f} from anything in {host!r}",
                        expected=f"between {params.min_distance} and {params.max_distance}",
                    )
                )

        return self._report(
            good=good,
            total=checks,
            violations=violations,
            metrics={
                "distance": distance,
                "host_distance": host_distance,
            },
            evidence=evidence,
        )

    @classmethod
    def apply_params_model(cls) -> type[PortmanteauApplyParams]:
        return PortmanteauApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: PortmanteauApplyParams) -> Produced:
        """Propose every splice of every trade word into the host; keep what checks.

        `text` is the host and `params.source` is the same string, injected by the
        spine, which is what lets each candidate be verified against what it was
        made from without the caller saying it twice.

        The search is exhaustive and small: for a host of *n* letters and a trade
        of *w* words there are `w * (n+1)(n+2)/2` ways to replace a stretch, which
        for the shipped vocabularies is a few hundred and at most 859 (English
        `paraphernalia`). Every one is handed to this row's own `check` and most
        are thrown out. Nothing here decides what a blend is — the checker does,
        and this only decides what to ask it about.

        Ranked closest-sounding first, then by how much of the host survives, then
        by the seam. That order was chosen by measuring four against the attested
        corpus, not by taste; the alternatives and what they cost are in ADR 0043.
        """
        host = text.strip()
        vocabulary = params.trade(pack.lang)
        if not vocabulary:
            raise InvalidParams(
                self.id,
                "nothing to splice in; pass `domain` or `domain_words`",
            )

        # Best seam per distinct coinage: two ways of cutting can reach the same
        # string, and the flattering one is the one that describes it.
        proposed: dict[str, tuple[float, str]] = {}
        bare_host = _bare_letters(host)
        for word in vocabulary:
            for start in range(len(host) + 1):
                for end in range(start, len(host) + 1):
                    candidate = host[:start] + word + host[end:]
                    if _bare_letters(candidate) == bare_host:
                        continue
                    seam = _seam(host, start, end, word)
                    if candidate in proposed and proposed[candidate][0] <= seam:
                        continue
                    proposed[candidate] = (seam, word)

        found: list[Candidate] = []
        for candidate, (seam, word) in proposed.items():
            report = self.check(
                candidate,
                lang=pack.lang,
                source=host,
                splice=word,
                max_distance=params.max_distance,
                max_host_distance=params.max_host_distance,
                splice_lang=params.splice_lang,
            )
            if not report.satisfied:
                continue
            found.append(
                Candidate(
                    text=candidate,
                    metrics={
                        "distance": report.metrics["distance"],
                        "host_distance": report.metrics["host_distance"],
                        "seam": seam,
                    },
                )
            )

        if not found:
            raise NoCandidateWord(
                self.id, f"no word of the trade splices into {host!r} inside the band"
            )
        found.sort(
            key=lambda c: (
                c.metrics["distance"],
                c.metrics["host_distance"],
                c.metrics["seam"],
                c.text,
            )
        )
        return Produced(
            candidates=found[: params.max_results], truncated=len(found) > params.max_results
        )
