"""A trade's vocabulary, and the phrases its puns are made on.

A *domain* is what a shop sells. `paronomasia` displaces a word of a known
phrase by one close to it in sound; which displacements are any good depends
almost entirely on whether the word that lands belongs to the trade whose sign
it is going on. *Bread Pitt* is a bakery and *Brand Pitt* is nothing.

Shipped in core rather than in a data distribution, for ADR 0017's reason: a
lexicon describes a language, but these lists describe *the procedure being
run*. A bakery pun with a hairdresser's vocabulary is a different procedure,
in the way a lipogram with a different forbidden letter is still a lipogram
but a Denckring with different rings is a different device.

**Every word and phrase here was written for this project**, which is why it
carries no third-party licence and needs no quarantine under ADR 0013. The
Poesieautomat's 360 fillers are the precedent: authored rather than lifted,
and said so. The phrases are ordinary idioms and set expressions, chosen
because a pun only lands on something the reader already knows.

Two things the lists encode that no rule in the checker does, both measured
rather than assumed:

- **A phrase is chosen for where it can be displaced.** Displacing a function
  word produces nonsense — French `la` is 0.333 from `laque`, so an
  unrestricted search offers `laque vie en rose` for half the phrases in the
  language. The phrases here are ones whose *content* words have neighbours.
- **A trade needs vocabulary that sounds like something.** Measured across
  four trades, the optician's does not: its best displacements are inflections
  of a word already in the phrase — `frame` to `frames`, `lens` to `lenses` —
  which is morphology and not a pun. That trade ships anyway, with the
  weakness recorded in its own file, because pretending otherwise would be the
  catalogue definition promising more than the data delivers.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources

import yaml
from pydantic import BaseModel, Field, ValidationError

from denckring.core.protocol import Lang

#: Where the shipped domain files live.
DOMAIN_DIR = "denckring.data.domains"


class Blend(BaseModel):
    """One attested-shape coinage: what it reads, and the two words behind it.

    Carried as a triple rather than inferred from the coinage, because inference
    gets it wrong in the direction that matters. `Haarmonie` against `Harmonie`
    differs by a single inserted `a`, so a diff would report the joke as "a" and
    miss that the word now showing through is `Haar`. The splice is the claim,
    and a claim is declared.
    """

    coinage: str
    host: str
    splice: str
    #: The language the spliced word belongs to, when it is not the host's.
    #: `Imagin'hair` is English inside French, which is the commonest shape in
    #: the French register and was unreachable until the notation bridge landed.
    splice_lang: str | None = None


class TradeWords(BaseModel):
    """One language's half of a domain."""

    words: list[str] = Field(min_length=1)
    #: Optional since the phrase corpus landed. A trade is defined by its
    #: *vocabulary*; phrases are things to pun on, and where those come from is
    #: the reader's business (ADR 0020). Requiring them here is what pushed the
    #: first three trades into carrying phrases I had invented and chosen for
    #: reachability — `Alles klar`, `Klar gewinnt` — rather than ones anybody
    #: says. A trade may now ship a vocabulary and no phrases at all, and the
    #: explorer's harvested corpus supplies what it shows.
    phrases: list[str] = Field(default_factory=list)
    #: Optional: a language may have a vocabulary and no blends written for it
    #: yet, which is a gap and not a malformed file.
    blends: list[Blend] = Field(default_factory=list)


class Domain(BaseModel):
    """A trade: what it sells, in each language it has been written for."""

    id: str
    names: dict[str, str]
    source: str
    #: Keyed by language. A trade need not exist in every language — the German
    #: salon window and the French boulangerie are different institutions, and
    #: writing an English optician's list in French to fill the table would be
    #: inventing evidence about a tradition nobody checked.
    languages: dict[str, TradeWords]

    def words(self, lang: Lang) -> tuple[str, ...]:
        """The trade's vocabulary in `lang`, or empty if it has none."""
        entry = self.languages.get(lang)
        return tuple(entry.words) if entry else ()

    def phrases(self, lang: Lang) -> tuple[str, ...]:
        """Phrases worth punning on in `lang`, or empty if there are none."""
        entry = self.languages.get(lang)
        return tuple(entry.phrases) if entry else ()

    def blends(self, lang: Lang) -> tuple[Blend, ...]:
        """Coinages for `lang`, or empty if none have been written."""
        entry = self.languages.get(lang)
        return tuple(entry.blends) if entry else ()

    def speaks(self, lang: Lang) -> bool:
        """Whether this trade has a vocabulary in `lang`.

        Vocabulary, not phrases: the vocabulary is what every procedure reads,
        and a trade with words and no phrases is a complete trade.
        """
        return lang in self.languages


def ids() -> tuple[str, ...]:
    """Every shipped domain id, sorted."""
    return tuple(
        sorted(
            entry.name.removesuffix(".yaml")
            for entry in resources.files(DOMAIN_DIR).iterdir()
            if entry.name.endswith(".yaml")
        )
    )


@lru_cache(maxsize=8)
def load(domain_id: str) -> Domain:
    """One shipped domain by id.

    Raises `KeyError` naming what was available, which the caller turns into
    whatever error suits it — `paronomasia` raises `InvalidParams`, because to
    that row a domain is a parameter value and a wrong one is a wrong argument
    rather than a missing file.

    `domain_id` must be a bare stem: no separator, no `..`, no absolute path.
    Unlike `device.load` there is no search path and no cartridge, so there is
    nothing to shadow — these lists are part of the procedure, and a caller who
    wants their own vocabulary passes `domain_words` directly instead.
    """
    available = ids()
    if domain_id not in available:
        raise KeyError(f"unknown domain {domain_id!r}; available: {', '.join(available)}")
    text = (resources.files(DOMAIN_DIR) / f"{domain_id}.yaml").read_text(encoding="utf-8")
    try:
        return Domain.model_validate(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError) as exc:  # pragma: no cover - shipped files are valid
        raise ValueError(f"domain {domain_id!r} is not readable as a domain") from exc


__all__ = ["Blend", "Domain", "TradeWords", "ids", "load"]
