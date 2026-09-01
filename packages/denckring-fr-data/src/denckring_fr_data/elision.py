"""French verse counts a line, not a sequence of words (spec D3).

A final mute e is a syllable before a consonant, elides before a vowel or a
mute h, and never counts at the end of a line. Lexique gives citation forms --
`femme`, `une`, `belle` and `porte` are all one syllable there and frequently
two in verse -- so summing them undercounts systematically.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

VOWELS = frozenset("aeiouyàâéèêëîïôöùûüœæ")
_VOWEL_RUN = re.compile(r"[aeiouyàâéèêëîïôöùûüœæ]+")

#: Proclitics whose own vowel is already elided in the spelling. They carry no
#: syllable, but they are CONSONANTS for the word in front of them: in
#: "ne t'attendais" the schwa of `ne` cannot elide across the `t'`. Dropping
#: them from the token stream cost six points in the go/no-go prototype.
ELIDED_ZERO: frozenset[str] = frozenset({"l", "d", "j", "n", "m", "t", "s", "c", "qu"})
#: Same, but these carry syllables: `lorsqu'il` is lors-qu'il.
ELIDED_WORD: dict[str, str] = {
    "lorsqu": "lorsque",
    "puisqu": "puisque",
    "quoiqu": "quoique",
    "jusqu": "jusque",
}

#: Word-shaped tokens, letters plus an optional trailing apostrophe. The
#: trailing apostrophe is what turns "t'attendais" into two tokens, "t'" and
#: "attendais", instead of losing the proclitic to a hyphen/apostrophe split
#: entirely (TRAP 2). Hyphens and whitespace both fall outside `\w` in a
#: Unicode pattern, so a compound like "dit-elle" tokenises the same way.
_TOKEN_RE = re.compile(r"[^\W\d_]+['’]?")  # noqa: RUF001


def latent_schwa(ortho: str, nbsyll: int, phon: str, orthosyll: str) -> tuple[int, bool]:
    """(syllables excluding any mute e, whether a mute e is pending).

    Lexique's SAMPA `@` is the nasal /ɑ̃/, NOT a schwa -- `dans` is `d@`.
    Schwa is `2`, which also spells /ø/, so `de` and `deux` are both `d2` and
    only the bare orthographic -e separates them.
    """
    suffix = next((s for s in ("ent", "es", "e") if ortho.endswith(s)), None)
    if suffix is None:
        return nbsyll, False
    if suffix == "e" and phon[-1:] in ("2", "°"):
        # `le`, `je`, `que`: Lexique counted the schwa, so take it back out.
        return max(nbsyll - 1, 0), True
    if len(orthosyll.split("-")) > nbsyll:
        # `bel-le` against 1 shows the mute e; `sou-vent` against 2 does not.
        return nbsyll, True
    if suffix == "ent":
        # orthosyll already judged it. `vient` strips to `vi`, whose one vowel
        # run matches nbsyll 1, so the fallback below would invent a mute e.
        return nbsyll, False
    # orthosyll merges the mute e after a vowel (`vie`, `joie`, `an-née`), so
    # fall back to vowel letter-runs. `qu`/`gu` carry a silent u.
    stripped = ortho[: -len(suffix)].replace("qu", "k").replace("gu", "g")
    return nbsyll, len(_VOWEL_RUN.findall(stripped)) == nbsyll


def _estimate(ortho: str) -> tuple[int, bool]:
    """A vowel-run guess for a word Lexique does not carry.

    `line_syllables` must degrade gracefully rather than raise -- unlike
    `syllables()`/`phonemes()`, which raise `MissingCapability` for exactly
    this case (Task 5). A real line of French routinely holds a word outside
    Lexique's 125,653 rows, and one unknown word must not blank the count for
    the whole line. Deliberately excludes `-ent` from the suffix check TRAP 3
    warns about: with no `orthosyll` to consult, there is no way to tell
    `chantent` from `vient`, so the safer default is to never invent a mute e
    there at all.
    """
    suffix = next((s for s in ("es", "e") if ortho.endswith(s) and ortho != s), None)
    if suffix is None:
        return max(len(_VOWEL_RUN.findall(ortho)), 1), False
    stripped = ortho[: -len(suffix)]
    return max(len(_VOWEL_RUN.findall(stripped)), 1), True


def _lookup(ortho: str, table: Mapping[str, tuple[int, str, str]]) -> tuple[int, bool, bool]:
    """(syllables excluding a pending mute e, mute e pending, estimated)."""
    entry = table.get(ortho)
    if entry is None:
        count, pending = _estimate(ortho)
        return count, pending, True
    nbsyll, phon, orthosyll = entry
    count, pending = latent_schwa(ortho, nbsyll, phon, orthosyll)
    return count, pending, False


def starts_with_vowel(word: str, aspire: frozenset[str]) -> bool:
    """Whether the token that follows lets a preceding mute e elide.

    A word starting with a vowel letter elides a schwa in front of it, and so
    does a mute h -- silent, letting the vowel behind it show. An aspirated h
    (Task 3's list) behaves as a consonant instead: "je hais" keeps `je`'s
    schwa where "une heure" loses `une`'s.
    """
    if not word:
        return False
    if word[0] in VOWELS:
        return True
    return word[0] == "h" and word not in aspire


def count_line(
    line: str, table: Mapping[str, tuple[int, str, str]], aspire: frozenset[str]
) -> tuple[int, int]:
    """(syllables in the line, words whose count was estimated).

    Tokenises on letters plus a trailing apostrophe, so an elided proclitic
    ("t'", "d'", "qu'") survives in the stream as its own zero-syllable,
    consonant-initial token -- TRAP 2: dropping it would let the preceding
    word's schwa see the vowel behind the proclitic and elide across it,
    which it must not.

    Walks the tokens once, adding one syllable for each pending mute e whose
    successor is consonant-initial. A pending mute e with no successor -- the
    line's last token -- is never added, which is how "the final e never
    counts at the end of a line" falls out of "not last" rather than needing
    a separate rule.
    """
    tokens = _TOKEN_RE.findall(line)
    # Each entry: (syllables carried, mute e pending, was estimated, text
    # used to judge whether the NEXT word starts with a vowel).
    parsed: list[tuple[int, bool, bool, str]] = []
    for token in tokens:
        lower = token.casefold()
        if lower.endswith(("'", "’")):  # noqa: RUF001
            stem = lower[:-1]
            if stem in ELIDED_ZERO:
                parsed.append((0, False, False, stem))
                continue
            full = ELIDED_WORD.get(stem)
            if full is not None:
                entry = table.get(full)
                if entry is not None:
                    # `lorsqu'il` etc: already elided in the spelling, so the
                    # mute e is gone, not merely pending.
                    count, _pending = latent_schwa(full, *entry)
                    parsed.append((count, False, False, stem))
                    continue
            # An elided proclitic this table doesn't recognise -- treat as
            # the silent consonant it spells rather than crashing the line.
            parsed.append((0, False, False, stem))
            continue
        count, pending, estimated = _lookup(lower, table)
        parsed.append((count, pending, estimated, lower))

    total = 0
    estimated_words = 0
    last = len(parsed) - 1
    for index, (count, pending, was_estimated, _text) in enumerate(parsed):
        total += count
        if was_estimated:
            estimated_words += 1
        if pending and index < last:
            successor = parsed[index + 1][3]
            if not starts_with_vowel(successor, aspire):
                total += 1
    return total, estimated_words
