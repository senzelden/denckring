"""Harvest a phrase corpus for the shopfront scene, and keep only what puns.

Run by hand, not at import: the output is committed beside this script so a page
render never waits on Wikidata, and so what the scene shows can be read and
audited as a file rather than re-derived from a query nobody sees.

    uv run python scripts/build_phrases.py

**Why this exists.** The trades' own `phrases` lists were written by me and
chosen for *mechanical reachability* — does a trade word land inside the band? —
which produced things like `Alles klar` and `Ganz klar`: real German, and not
phrases anybody would put over a shop. A pun lands on something the reader
already knows, and the way to get those is to take them from a corpus of things
people actually say rather than to invent them.

**Why here and not in the library.** ADR 0020 says a corpus is supplied by the
reader, and that stays true: `denckring` ships no corpus and `apply` still takes
one phrase from its caller. The explorer is a local bench marked
`Private :: Do Not Upload`, so a corpus can live here without the licence
quarantine ADR 0013 would demand of a published distribution.

**Source and licence.** Film titles from Wikidata, which is **CC0** — no
attribution required, though `data/phrases/NOTICE` records it anyway. Only films
whose original language is the language being harvested, so the titles are ones a
speaker of it would recognise rather than translations.

**What is kept.** A title survives only if it yields a pun *for a given trade*
inside the band, and the file is written per (trade, language) already filtered.
Scanning eighteen hundred titles takes about twenty seconds; doing it on every
page render would make the scene unusable, and doing it at import would make it
unusable and mysterious.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from denckring import produce
from denckring.core import domain as domains

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "src" / "explorer" / "data" / "phrases"

#: Wikidata item ids for the languages, for `wdt:P364` (original language).
LANGUAGE_ITEM = {"de": "Q188", "en": "Q1860", "fr": "Q150"}

#: Function words, per language. Displacing one produces nonsense — `sur`
#: becomes `sucre` and `Le Déjeuner sur l'herbe` becomes `Le Déjeuner sucre
#: l'herbe`, which is not a pun but a broken sentence. The hand-written phrase
#: lists were curated against exactly this and the corpus arrived without the
#: guard, so it moves here.
#:
#: A closed class, so listing it is not inventing data the way a phrase list
#: would be. Deliberately NOT a length rule: `Die Hard` gives `Dye Hard`, the
#: best English name in the set, and `Die` is three letters like `sur` is.
#: What separates them is grammar, not size.
FUNCTION_WORDS: dict[str, frozenset[str]] = {
    "de": frozenset(
        [
            "der",
            "die",
            "das",
            "den",
            "dem",
            "des",
            "ein",
            "eine",
            "einer",
            "eines",
            "einem",
            "einen",
            "und",
            "oder",
            "aber",
            "in",
            "im",
            "an",
            "am",
            "auf",
            "aus",
            "bei",
            "mit",
            "nach",
            "von",
            "vor",
            "zu",
            "zum",
            "zur",
            "über",
            "unter",
            "durch",
            "für",
            "ist",
            "sind",
            "war",
            "waren",
            "wird",
            "werden",
            "hat",
            "haben",
            "ich",
            "du",
            "er",
            "sie",
            "es",
            "wir",
            "ihr",
            "sich",
            "nicht",
            "kein",
            "keine",
            "als",
            "wie",
            "wenn",
            "dass",
            "da",
            "so",
            "noch",
            "nur",
            "auch",
            "schon",
            "mal",
        ]
    ),
    "en": frozenset(
        [
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "of",
            "in",
            "on",
            "at",
            "to",
            "from",
            "with",
            "by",
            "for",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "it",
            "its",
            "his",
            "her",
            "their",
            "our",
            "your",
            "my",
            "this",
            "that",
            "these",
            "those",
            "as",
            "if",
            "not",
            "no",
            "than",
            "then",
            "there",
            "here",
            "who",
            "whom",
            "which",
            "what",
            "when",
            "where",
            "how",
            "all",
            "any",
            "some",
            "into",
            "over",
            "under",
            "up",
            "down",
            "out",
            "off",
        ]
    ),
    "fr": frozenset(
        [
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "du",
            "de",
            "au",
            "aux",
            "et",
            "ou",
            "mais",
            "en",
            "dans",
            "sur",
            "sous",
            "par",
            "pour",
            "avec",
            "sans",
            "chez",
            "vers",
            "est",
            "sont",
            "était",
            "étaient",
            "sera",
            "a",
            "ont",
            "il",
            "elle",
            "ils",
            "elles",
            "je",
            "tu",
            "nous",
            "vous",
            "se",
            "ce",
            "cet",
            "cette",
            "ces",
            "qui",
            "que",
            "quoi",
            "dont",
            "où",
            "ne",
            "pas",
            "plus",
            "très",
            "bien",
            "tout",
            "tous",
            "toute",
            "toutes",
            "son",
            "sa",
            "ses",
            "leur",
            "leurs",
            "mon",
            "ma",
            "mes",
        ]
    ),
}

#: How many phrases to keep per trade. Forty is enough that the scene never
#: repeats itself within a session and small enough that the file can be read.
KEEP = 40

QUERY = (
    "SELECT DISTINCT ?label WHERE {{ "
    "?f wdt:P31 wd:Q11424 ; wdt:P364 wd:{item} ; rdfs:label ?label . "
    'FILTER(LANG(?label)="{lang}") }} LIMIT 4000'
)


def titles(lang: str) -> list[str]:
    """Film titles in `lang`, for films originally made in it."""
    query = QUERY.format(item=LANGUAGE_ITEM[lang], lang=lang)
    request = urllib.request.Request(
        "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query}),
        headers={
            "Accept": "application/sparql-results+json",
            # Wikidata asks for a descriptive agent; an anonymous one gets throttled.
            "User-Agent": "denckring-explorer/0.1 (phrase corpus for a local bench)",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    found = {row["label"]["value"] for row in payload["results"]["bindings"]}
    # Two to five words, letters only: a one-word title has nothing to displace
    # around, and anything with digits or punctuation reads badly on a sign.
    return sorted(
        t
        for t in found
        if 2 <= len(t.split()) <= 5 and re.fullmatch(r"[^\W\d_ '-]+(?:[ '-][^\W\d_ '-]+)*", t)
    )


def _displaces_a_function_word(title: str, coinage: str, lang: str) -> bool:
    """Whether the word that was pushed out is a function word.

    Compared position by position, which is what `paronomasia` itself does: the
    generator substitutes in place, so the two texts have the same word count and
    differ at exactly the position that was displaced.
    """
    stop = FUNCTION_WORDS[lang]
    before, after = title.split(), coinage.split()
    if len(before) != len(after):
        return False
    return any(
        original.casefold().strip("'\u2019-") in stop
        for original, landed in zip(before, after, strict=True)
        if original.casefold() != landed.casefold()
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for lang in LANGUAGE_ITEM:
        pool = titles(lang)
        print(f"{lang}: {len(pool)} titles", file=sys.stderr)
        for trade_id in domains.ids():
            trade = domains.load(trade_id)
            if not trade.speaks(lang):  # type: ignore[arg-type]
                continue
            hits: list[tuple[float, str]] = []
            for title in pool:
                try:
                    candidate = produce(
                        "paronomasia",
                        title,
                        lang=lang,  # type: ignore[arg-type]
                        domain=trade_id,
                        domain_only=True,
                        max_results=1,
                    ).candidates[0]
                except Exception:
                    continue
                if not candidate.metrics["in_trade"]:
                    continue
                if _displaces_a_function_word(title, candidate.text, lang):
                    continue
                hits.append((candidate.metrics["distance"], title))
            hits.sort()
            kept = [title for _, title in hits[:KEEP]]
            path = OUT / f"{trade_id}_{lang}.txt"
            path.write_text("\n".join(kept) + "\n", encoding="utf-8")
            print(
                f"  {trade_id}/{lang}: kept {len(kept)} of {len(hits)} that punned", file=sys.stderr
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
