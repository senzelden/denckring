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

#: SAMPA consonants (Lexique's alphabet, `sampa.SAMPA_TO_IPA` minus the
#: vowels and the three glides j/w/8). Used only by the diérèse pass below.
_SAMPA_CONSONANTS = frozenset("bdfgklmnNpRsStvzZGx")


def _dierese_extra(ortho: str, phon: str) -> int:
    """Extra syllables classical diérèse adds to Lexique's citation count.

    ADR 0034. Classical French diérèse -- whether a Latin/Greek-derived `i`
    or `u` glide (`diadème`, `division`) counts as its own syllable, as
    against a native word's fixed glide (`pied`, `moindre`) that never does
    -- is etymological, not spelling-derived (Task 7 brief). The rule
    shipped here: every `j` after any consonant, single or a cluster, is an
    extra syllable, gated on the word ending in the `-ion(s)` noun suffix
    (the textbook diérèse site: Latin `-io`/`-ionem`) or starting with
    `dia-`. Measured against Racine's *Mithridate* and Hugo's *Hernani*
    (interior lines only; the harness that produced the table below was a
    throwaway script, per spec, and is not shipped -- ADR 0034 D5 carries
    the rule and the table, not the method), this is **Racine 89.3% ->
    90.3%, Hugo 79.3% -> 80.2%**, against a
    diérèse ceiling of 96.6%/84.8% -- a mechanical rule takes about 1.0 of
    the 7.3 points a perfect per-site oracle would.

    Three mechanical variants were measured on the way here, none of which
    ships unchanged:

    - a glide after a consonant CLUSTER ending in a liquid (R, l): worse
      than no rule at all on both texts (84.5%/74.7% against the
      89.3%/79.3% baseline);
    - every `j` after a single consonant, excluding verb-inflection and
      adjective endings that are reliably synérèse (`-iez`, `-ions`, `-ier`,
      `-ien`, `-iable`, `-iant`, `-iance` and their plurals/feminines) --
      those grammatical endings are the plurality of every "j after a single
      consonant" site in the whole Lexique table, which is why a still
      blunter blanket rule scored a catastrophic 49.5%/36.6%; excluding them
      only brought it to 86.7%/70.0%, still below baseline on Hugo;
    - `j` after a single consonant, narrowed further to the `-ion(s)` noun
      suffix and the `dia-` prefix: the only variant that beat baseline on
      BOTH texts, measured **as tried, with the single-consonant
      restriction still in place, at 90.3%/80.0%**.

    The `-ion(s)`/`dia-` gate is the shape that third variant kept. Its
    single-consonant restriction was not: fix round 1 found it carried over
    from the first, rejected variant (cluster-ending-in-a-liquid) without
    independent justification, isolated it, and measured it as actively
    costing 0.2 points on Hugo -- for no gain on Racine -- by wrongly
    suppressing `factions` and `predictions`, both genuine `-ion` diérèse
    sites whose `j` follows a `ks`/`ts` cluster. It was dropped; every `j`
    after any consonant now counts once the gate passes, which is the
    90.3%/80.2% above, not the 90.3%/80.0% the gated variant measured.

    None of the three reached the 94% accept bar -- this is a STOP, not an
    ACCEPT -- so it ships as the honest ceiling of a three-variant budget,
    not a solved rule: `line_syllables`'s count stays an estimate
    (spec D4), never dictionary-exact. `w` and `8` are left out entirely:
    they overwhelmingly spell native `oi`/`ou`/`ui` digraphs that are never
    split, and no variant that touched them improved on one that ignored
    them.

    Whole-branch review (2026-09-01) found an undocumented `-iation`/`-iations`
    exclusion on the `-ion(s)` gate -- present in code, named nowhere: not
    here, not in ADR 0034 D5, not in the plan. Re-measured against Racine and
    Hugo interior lines with and without it: **identical to four significant
    figures both ways, 90.3%/80.2%**, because neither corpus contains a
    French `-iation`/`-iations` word at all (the only hits are English
    "appreciation"/"abbreviation"/"associations" in Hugo's front matter,
    outside any verse block). An exclusion with no measured effect and no
    citable justification earns nothing, so it was dropped rather than
    documented: `aviation`, `association` and `initiation` now take diérèse
    like any other `-ion(s)` word, on the same unverified footing as the
    rest of the gate.
    """
    is_ion = ortho.endswith(("ion", "ions"))
    if not (is_ion or ortho.startswith("dia")):
        return 0
    extra = 0
    for index, char in enumerate(phon):
        if char != "j" or index == 0 or phon[index - 1] not in _SAMPA_CONSONANTS:
            continue
        extra += 1
    return extra


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

#: Word-shaped tokens, keeping an internal apostrophe joined rather than
#: splitting on it -- the same shape as `denckring.lang.base.WORD_RE`. Fix
#: round 1: splitting unconditionally corrupted the 94 Lexique entries keyed
#: WITH an internal apostrophe (`aujourd'hui`, `prud'homme`), which are real
#: single words, not a proclitic plus a word -- `count_line` tries the whole
#: token against the table first and only falls back to splitting when that
#: fails (`l'ami` is not a table entry, so it still splits). Hyphens and
#: whitespace both fall outside `\w` in a Unicode pattern, so a compound like
#: "dit-elle" tokenises as two tokens without any special case for the hyphen.
_TOKEN_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")  # noqa: RUF001


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


def _judge(ortho: str, entry: tuple[int, str, str]) -> tuple[int, bool, bool]:
    """(syllables excluding a pending mute e, mute e pending, judged).

    A table hit's `nbsyll` is a citation fact, not a guess -- Lexique's
    dictionary count for a known spelling is exact. What sits on top of it is
    not: whether a mute e is pending (elides or counts depending on the next
    word) and whether classical diérèse adds a syllable are both editorial
    judgments the spelling alone does not settle (`extraordinaire` is five
    syllables or six depending on the poet, D5's own example). Finding 3 of
    the whole-branch review: spec D4 and ADR 0034 both say the French line
    count is `exact=False`, always, and before this the flag only fired on an
    out-of-vocabulary word -- a line entirely of known words with a pending
    mute e or a diérèse site reported `estimated_words == 0`, confidently
    wrong in the D4/`test_prosody_robustness`-flagged sense. `judged` is True
    when either call was made, so `count_line` can fold it into the same
    `estimated_words` counter it already keeps for out-of-vocabulary words.
    """
    nbsyll, phon, orthosyll = entry
    count, pending = latent_schwa(ortho, nbsyll, phon, orthosyll)
    extra = _dierese_extra(ortho, phon)
    return count + extra, pending, pending or extra > 0


def _lookup(ortho: str, table: Mapping[str, tuple[int, str, str]]) -> tuple[int, bool, bool]:
    """(syllables excluding a pending mute e, mute e pending, estimated).

    Diérèse (Task 7, ADR 0034) is added here rather than at the caller: it is
    a property of the word's own phonetics, the same footing as the mute-e
    count it sits beside, and an unknown word (`_estimate`) has no `phon` to
    judge it by, so the diérèse pass only ever runs on a table hit.

    `estimated` covers two different reasons now (Finding 3): a word outside
    Lexique altogether (`_estimate`, always estimated), and a table hit whose
    count rests on a mute-e or diérèse judgment (`_judge`, delegated to it).
    """
    entry = table.get(ortho)
    if entry is None:
        count, pending = _estimate(ortho)
        return count, pending, True
    return _judge(ortho, entry)


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


def _split_at_apostrophe(word: str) -> tuple[str, str]:
    """(stem before the first apostrophe, everything after it).

    Called only once the whole token has already failed a table lookup, so
    this never runs on `aujourd'hui` or `prud'homme` -- both are single
    Lexique entries and are used whole (fix round 1).
    """
    for index, ch in enumerate(word):
        if ch in ("'", "’"):  # noqa: RUF001
            return word[:index], word[index + 1 :]
    return word, ""


def count_line(
    line: str, table: Mapping[str, tuple[int, str, str]], aspire: frozenset[str]
) -> tuple[int, int]:
    """(syllables in the line, words whose count was estimated).

    "Estimated" covers three cases now, all folded into one counter (Finding
    3 of the whole-branch review, spec D4): a word outside Lexique
    (`_estimate`'s vowel-run guess), a word carrying a pending mute e, and a
    word whose diérèse gate fired. The first is out-of-vocabulary; the other
    two are in-vocabulary but their contribution to the count rests on an
    editorial judgment the spelling does not settle -- which is exactly what
    D4 means by "estimated, never exact." Before this fix a line built
    entirely from known words could carry a mute-e or diérèse judgment and
    still report `estimated_words == 0`, the confidently-wrong shape D4
    exists to rule out.

    A token that carries an internal apostrophe is tried WHOLE against the
    table first: 94 Lexique entries are keyed with one (`aujourd'hui`,
    `prud'homme`), and splitting them unconditionally silently returned a
    confidently wrong count with `estimated` left at 0 -- fix round 1's
    finding, and the failure mode this project cares most about, a wrong
    answer reported as certain. Only a token the table does not recognise
    whole falls back to splitting at the apostrophe and treating the stem as
    a proclitic ("t'", "d'", "qu'") -- a zero-syllable, consonant-initial
    token that survives in the stream rather than being dropped, which is
    TRAP 2: dropping it would let the preceding word's schwa see the vowel
    behind the proclitic and elide across it, which it must not.

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
        if "'" not in lower and "’" not in lower:  # noqa: RUF001
            count, pending, estimated = _lookup(lower, table)
            parsed.append((count, pending, estimated, lower))
            continue
        entry = table.get(lower)
        if entry is not None:
            # `aujourd'hui`, `prud'homme`: a fused word, not a proclitic plus
            # a word -- 94 Lexique entries carry an internal apostrophe.
            count, pending, judged = _judge(lower, entry)
            parsed.append((count, pending, judged, lower))
            continue
        # The whole form isn't a table entry, so it wasn't a fused word like
        # those -- read the apostrophe as an elision boundary instead.
        stem, rest = _split_at_apostrophe(lower)
        if stem in ELIDED_ZERO:
            parsed.append((0, False, False, stem))
        elif (full := ELIDED_WORD.get(stem)) is not None and (
            word_entry := table.get(full)
        ) is not None:
            # `lorsqu'il` etc: already elided in the spelling, so the mute e
            # is gone, not merely pending -- `pending` stays False regardless
            # of what `latent_schwa` would say about `full` on its own. A
            # diérèse site is still a live judgment here, so it alone decides
            # `estimated` (Finding 3).
            nbsyll, phon, orthosyll = word_entry
            count, _pending = latent_schwa(full, nbsyll, phon, orthosyll)
            extra = _dierese_extra(full, phon)
            parsed.append((count + extra, False, extra > 0, stem))
        else:
            # An elided proclitic neither list recognises -- there is no
            # basis for a confident zero, so flag it estimated rather than
            # silently asserting one (fix round 1, same defect as the
            # whole-token case above, now on the proclitic path).
            parsed.append((0, False, True, stem))
        if rest:
            count, pending, estimated = _lookup(rest, table)
            parsed.append((count, pending, estimated, rest))

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
