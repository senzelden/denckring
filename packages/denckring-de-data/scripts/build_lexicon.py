"""Regenerate the vendored German lexicon from Wikidata Lexemes.

Committed so the data files are reproducible and diffable. CMUdict in the
English package is not, and a second opaque blob is not worth adding.

    python scripts/build_lexicon.py

Wikidata Lexemes are CC0: no attribution, no share-alike. See LICENSE-WIKIDATA.
"""

from __future__ import annotations

import gzip
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

#: Network failure modes seen against the shared Wikidata Query Service:
#: HTTP errors, connection drops, and truncated chunked responses that leave
#: json.load with a malformed tail.
NETWORK_ERRORS = (
    urllib.error.HTTPError,
    urllib.error.URLError,
    http.client.HTTPException,
    json.JSONDecodeError,
)

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "denckring-de-data/0.1 (https://github.com/senzelden/denckring)"
DATA = Path(__file__).resolve().parents[1] / "src" / "denckring_de_data" / "data"
#: Beside the .gz files: the generation date and the two entry counts, so a
#: silent corpus change fails a test loudly instead of drifting unnoticed
#: (the gzip bytes alone do not diff cleanly enough to catch that by eye).
METADATA = DATA / "metadata.json"

#: German (Q188), noun (Q1084).
NOUN_LEMMAS = """
SELECT DISTINCT ?lemma WHERE {
  ?l dct:language wd:Q188 ; wikibase:lexicalCategory wd:Q1084 ; wikibase:lemma ?lemma .
}
"""

#: Every lexical category used by a German lexeme. Queried per-category below
#: because the single-query ALL_FORMS shape times out on the shared endpoint.
CATEGORIES = """
SELECT DISTINCT ?cat WHERE {
  ?l dct:language wd:Q188 ; wikibase:lexicalCategory ?cat .
}
"""

#: Every inflected form of German lexemes in one lexical category. Not nouns
#: alone: `charade` and `word_square` ask "is this a word", and a noun-only
#: oracle would reject `singen` and `rot`. The endpoint drops large single
#: queries, so the caller unions this per category (and paginates within a
#: category if even that is too large).
FORMS_BY_CATEGORY = """
SELECT DISTINCT ?rep WHERE {{
  ?l dct:language wd:Q188 ; wikibase:lexicalCategory <{category}> ; ontolex:lexicalForm ?f .
  ?f ontolex:representation ?rep .
}}
"""

#: Same query, paginated: for categories too large even on their own.
FORMS_BY_CATEGORY_PAGE = """
SELECT DISTINCT ?rep WHERE {{
  ?l dct:language wd:Q188 ; wikibase:lexicalCategory <{category}> ; ontolex:lexicalForm ?f .
  ?f ontolex:representation ?rep .
}}
ORDER BY ?rep
LIMIT {limit} OFFSET {offset}
"""

#: A noun the tokeniser returns whole: no spaces, no hyphens, no digits. ADR
#: 0015's rule for English, applied unchanged. Umlauts and ß are kept — folding
#: them here would collide `Bär` with `Bar`, and ADR 0009 makes folding a
#: procedure parameter rather than a property of the data.
SINGLE_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß]{2,}")

PAGE_SIZE = 100_000


def query(sparql: str, attempts: int = 4, wait_base: float = 8.0) -> list[str]:
    """Run one SPARQL query, retrying with backoff. Be a polite client:
    this hits the shared public Wikidata Query Service."""
    url = f"{ENDPOINT}?{urllib.parse.urlencode({'query': sparql})}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                payload = json.load(response)
            rows = payload["results"]["bindings"]
            return [next(iter(row.values()))["value"] for row in rows]
        except NETWORK_ERRORS as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            wait = wait_base * (attempt + 1)
            print(f"    retry after {exc!r}, waiting {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def forms_for_category(category: str) -> list[str]:
    """All representations for one lexical category, falling back to
    LIMIT/OFFSET pagination if the category is too large for one response."""
    try:
        return query(FORMS_BY_CATEGORY.format(category=category), attempts=2)
    except NETWORK_ERRORS:
        print(f"    {category}: paginating", file=sys.stderr)

    results: list[str] = []
    offset = 0
    while True:
        page = query(
            FORMS_BY_CATEGORY_PAGE.format(category=category, limit=PAGE_SIZE, offset=offset)
        )
        results.extend(page)
        if len(page) < PAGE_SIZE:
            return results
        offset += PAGE_SIZE
        time.sleep(2)


def all_forms() -> set[str]:
    #: casefold(), not lower(): German has no reliable native uppercase ß, so
    #: casefold() maps ß -> "ss" (str.lower() would keep ß but then miss an
    #: all-caps "STRASSE" and split Straße/Strasse into unrelated words,
    #: which is worse). This deliberately merges Swiss and German spellings
    #: of the same word (Anstoßkreis/Anstosskreis) in words.txt.gz. Measured
    #: impact: 110 collision keys covering 222 of 184,040 noun lemmas
    #: (0.12%), all either ß/ss spelling variants or acronym case variants
    #: (AIDS/Aids) - correct behaviour for a membership oracle, not lossy.
    #: nouns.txt.gz keeps ß intact (see main()); only the membership set is
    #: folded. Any consumer of words.txt.gz must casefold its query input
    #: too, or lookups for ß-containing words will silently miss.
    forms: set[str] = set()
    for category in query(CATEGORIES):
        rows = forms_for_category(category)
        print(f"    {category}: {len(rows):,} forms", file=sys.stderr)
        forms.update(w.casefold() for w in rows if SINGLE_TOKEN.fullmatch(w))
        time.sleep(2)
    return forms


def write(path: Path, entries: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(entries).encode("utf-8")
    # mtime=0: gzip embeds a timestamp by default, so two runs over identical
    # content would otherwise produce different bytes and `git diff` would
    # show "Binary files differ" even when nothing changed.
    path.write_bytes(gzip.compress(payload, mtime=0))
    print(f"  {path.name}: {len(entries):,} entries", file=sys.stderr)
    return len(entries)


def write_metadata(noun_count: int, word_count: int) -> None:
    """Record beside the .gz files what generated them and how many entries
    they hold, so a test can assert the shipped files still match and a
    silent corpus change fails loudly instead of drifting unnoticed."""
    metadata = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
        "source": "Wikidata Lexemes (Q188, German), CC0 - see LICENSE-WIKIDATA and this script",
        "counts": {"nouns.txt.gz": noun_count, "words.txt.gz": word_count},
    }
    METADATA.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  {METADATA.name}: {metadata}", file=sys.stderr)


def main() -> int:
    lemmas = [w for w in query(NOUN_LEMMAS) if SINGLE_TOKEN.fullmatch(w) and w[:1].isupper()]
    nouns = sorted(set(lemmas))
    noun_count = write(DATA / "nouns.txt.gz", nouns)

    forms = all_forms()
    forms.update(w.casefold() for w in nouns)  # same ß -> ss folding, see all_forms()
    word_count = write(DATA / "words.txt.gz", sorted(forms))

    write_metadata(noun_count, word_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
