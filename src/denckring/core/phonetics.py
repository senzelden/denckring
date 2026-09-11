"""How far apart two pronunciations are, as a number between 0 and 1.

This is the measure `paronomasia`'s band is expressed in: 0.0 is a homophone,
and a rising value is a pun working harder. It is one committed reading of
"phonetic distance" among several, in the way `text_folding` commits to one
reading of a fold and `mathews_algorithm` to one reading of "read across" —
namely **normalised Levenshtein over phoneme symbols, every edit costing one**.

The alternative worth naming, because the research this row came from
recommends it, is a feature-weighted distance (PanPhon's PFER, or ALINE), where
a voicing-only swap `/t/`→`/d/` costs less than `/t/`→`/m/`. That is the more
perceptually faithful measure and it is deliberately not used here. It would
put numpy and pandas behind a package whose dependencies are pydantic, pyyaml
and typer, and which claims free-threading support; and it needs one feature
table per notation, where this needs none. The cost is real and is admitted:
this measure cannot tell a near-miss consonant from a distant one, so a band
tuned on vowels will not behave the same way on consonants.

Nothing here converts between notations, and nothing needs to. The three packs
answer in three alphabets — English ARPABET, German IPA, French IPA via
SAMPA — but a pun is made inside one language, so both sides of any comparison
come from the same pack and are already commensurable. Comparing across
languages is `phonemes.bilingual`, which no pack provides.
"""

from __future__ import annotations

from collections import Counter

#: Symbols a language's own notation spells differently for one segment.
#:
#: German is the case that forced this. A syllable-final /r/ vocalises — `Haar`
#: is transcribed `h aː ɐ̯` and `Harmonie` is `h a ʁ m o n iː` — so the same
#: underlying r appears as `ɐ̯` in one and `ʁ` in the other. An unweighted edit
#: distance charges a full substitution for that, which put `Haar` 0.667 from
#: the opening of `Harmonie` and made the best-known German blend in the
#: tradition unreachable by the row that catalogues it.
#:
#: Deliberately narrow, and the exclusions matter more than the inclusions:
#:
#: - **Vowel length is NOT folded.** `aː` and `a` are contrastive in German —
#:   `Staat` and `Stadt` are different words — so collapsing them would buy
#:   `Haarmonie` a distance of 0.000 by discarding a distinction the language
#:   actually makes. It sits at 0.333 instead, which is honest.
#: - Nothing is folded for English or French. ARPABET has no vocalised-r
#:   symbol, and Lexique's SAMPA maps to a single `ʁ`. A table entry for them
#:   would be a guess dressed as data.
#:
#: Measured before it shipped: folding changes **no** existing verdict. All nine
#: German pairs in the shipped fixtures and domain phrases score identically
#: with and without it, so this is additive rather than a re-reading of work
#: already checked.
EQUIVALENT: dict[str, tuple[frozenset[str], ...]] = {
    "de": (frozenset({"ʁ", "ɐ̯", "ɐ", "r"}),),
}


def fold_equivalents(phonemes: list[str], lang: str | None) -> list[str]:
    """Rewrite each phoneme to the representative of its equivalence class.

    A no-op for a language with no table, and for `lang=None` — which is what a
    caller comparing two sequences of unknown provenance gets, and the right
    default: folding by the wrong language's rules is worse than not folding.
    """
    classes = EQUIVALENT.get(lang or "", ())
    if not classes:
        return phonemes
    canonical = {member: min(group) for group in classes for member in group}
    return [canonical.get(phoneme, phoneme) for phoneme in phonemes]


def bare_phonemes(phonemes: list[str]) -> list[str]:
    """The phonemes with ARPABET's stress digits removed.

    CMUdict writes stress as a digit on the vowel — `EH1`, `AH0` — so two
    pronunciations of one word differ as symbol strings while being the same
    sounds. Left in, `the` unstressed would read as a pun on `the` stressed.
    German and French hand back IPA, which marks stress with its own separate
    symbol (`ˈ`, `ˌ`) and never with a digit, so this is a no-op for them:
    the rule strips a *trailing digit*, not a character class.
    """
    return [phoneme[:-1] if phoneme[-1:].isdigit() else phoneme for phoneme in phonemes]


def phoneme_distance(
    a: list[str], b: list[str], lang: str | None = None, ceiling: float | None = None
) -> float:
    """Levenshtein over phoneme symbols, normalised by the longer sequence.

    0.0 is identical, 1.0 is wholly different — which includes a sequence
    against nothing, and equal-length sequences sharing no symbol at all. Two
    empty sequences are 0.0 rather than a division by zero: nothing differs.

    Normalising by the longer side rather than by the edit path keeps the
    result inside [0, 1] whatever the lengths, and keeps the measure symmetric,
    which a band expressed as an interval needs.

    `lang` opts into that language's equivalence classes (see `EQUIVALENT`).
    Omitted, nothing is folded — comparing two sequences without knowing whose
    notation they are in is exactly when guessing is worst.

    `ceiling` says the caller only cares whether the answer is at or below some
    value. A pair that is further comes back as *some* number above it rather
    than its true distance, which is why this is opt-in: a caller ranking
    results must not pass it, and a caller filtering them should.
    """
    left = fold_equivalents(bare_phonemes(a), lang)
    right = fold_equivalents(bare_phonemes(b), lang)
    longest = max(len(left), len(right))
    if longest == 0:
        return 0.0
    cutoff = int(ceiling * longest) if ceiling is not None else None
    return _levenshtein(left, right, cutoff) / longest


def _levenshtein(a: list[str], b: list[str], cutoff: int | None = None) -> int:
    """Edit distance with unit costs, over one row at a time.

    A full matrix would be clearer to read but this is called once per lexicon
    candidate in `paronomasia`'s generator, where the row-at-a-time form is what
    keeps a scan over tens of thousands of words affordable.

    `cutoff` abandons a comparison that has already lost. Once every cell in a
    row exceeds the largest number of edits the caller can accept, no completion
    of the matrix can come back under it — the values along a row never decrease
    as it fills — so the answer is "further than `cutoff`" and the remaining rows
    need not be computed. The value returned in that case is `cutoff + 1`, which
    is a truthful "at least this far" and never a real distance a caller could
    mistake for one.

    This is what pays for the prefilter being sound rather than clever. The old
    prefilter was fast because it was wrong: it discarded pairs that were inside
    the band. Doing the arithmetic honestly and abandoning it early is the same
    saving without the lost answers.
    """
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, start=1):
        current = [i]
        for j, right in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (left != right),  # substitution
                )
            )
        if cutoff is not None and min(current) > cutoff:
            return cutoff + 1
        previous = current
    return previous[-1]


#: CMUdict's 39 ARPABET symbols, in IPA.
#:
#: English is the only pack that answers in ARPABET; German and French already
#: give IPA, so this is the whole of what stands between them. Without it a
#: cross-lingual pun cannot be measured at all — `hair` is `HH EH R` and French
#: `air` is `ɛ ʁ`, and no amount of edit distance over those symbol sets means
#: anything.
#:
#: A table, deliberately, and not a model: 39 entries a reader can check against
#: the CMUdict phoneme list, with nothing that can be silently wrong. Stress
#: digits are stripped before lookup by `bare_phonemes`.
#:
#: Two entries carry a judgement and are called out rather than buried. `ER` is
#: given as `ɚ` and `R` as `ɹ`, both faithful to General American; they are then
#: folded together with `ʁ` and `ɐ̯` by `CROSS_LINGUAL` below, because a rhotic
#: is realised differently in every language here and a pun does not care which.
ARPABET_TO_IPA: dict[str, str] = {
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ʌ",
    "AO": "ɔ",
    "AW": "aʊ",
    "AY": "aɪ",
    "B": "b",
    "CH": "tʃ",
    "D": "d",
    "DH": "ð",
    "EH": "ɛ",
    "ER": "ɚ",
    "EY": "eɪ",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "IH": "ɪ",
    "IY": "i",
    "JH": "dʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "UH": "ʊ",
    "UW": "u",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}

#: Classes that hold *between* languages, applied only when comparing across
#: them. The rhotics are one category realised differently everywhere — English
#: `ɹ`, French and German `ʁ`, German's vocalised `ɐ̯`, a trilled `r` — and a
#: pun turns on the category, not the realisation. `hair` against French `air`
#: is the case: without this it is two edits apart and with it, one.
#:
#: Kept separate from `EQUIVALENT`, which is per-language and narrower. Folding
#: rhotics together inside English would say `ɹ` and `ɐ̯` are the same English
#: sound, which is not a claim this table is making.
CROSS_LINGUAL: tuple[frozenset[str], ...] = (frozenset({"ɹ", "ʁ", "r", "ɐ̯", "ɐ", "ɚ"}),)


def to_ipa(phonemes: list[str], lang: str) -> list[str]:
    """A pack's phonemes in IPA, whatever notation it answered in.

    English is mapped through `ARPABET_TO_IPA`; German and French are returned
    unchanged, because both already give IPA. A symbol with no entry is passed
    through rather than dropped — losing it would silently shorten a word and
    move every distance computed from it.
    """
    if lang != "en":
        return phonemes
    return [ARPABET_TO_IPA.get(symbol, symbol) for symbol in bare_phonemes(phonemes)]


def across_languages(a: list[str], a_lang: str, b: list[str], b_lang: str) -> float:
    """How far apart two pronunciations are when they come from different packs.

    Both sides are put into IPA and then folded by `CROSS_LINGUAL`, which is the
    only place rhotics from different languages are treated as one sound. This
    is what `homophonic_translation` has been blocked on as `phonemes.bilingual`
    since it was catalogued — the notation half of it, at least; that row needs a
    good deal more than a comparison.
    """
    left = fold_equivalents(to_ipa(a, a_lang), None)
    right = fold_equivalents(to_ipa(b, b_lang), None)
    canonical = {member: min(group) for group in CROSS_LINGUAL for member in group}
    left = [canonical.get(symbol, symbol) for symbol in left]
    right = [canonical.get(symbol, symbol) for symbol in right]
    return distance_prepared(left, right)


def prepared(phonemes: list[str], lang: str | None) -> list[str]:
    """The form the measure actually compares: stress stripped, equivalents folded.

    Exposed so a caller scanning a lexicon can do this **once per entry** instead
    of twice per comparison. `phoneme_distance` normalises its arguments every
    call, which is right for a caller with two words and wrong for one with two
    hundred thousand: the allocation, not the edit distance, was what made a full
    scan cost seconds. `distance_prepared` is the matching comparison.
    """
    return fold_equivalents(bare_phonemes(phonemes), lang)


def distance_prepared(a: list[str], b: list[str], ceiling: float | None = None) -> float:
    """`phoneme_distance` for arguments already through `prepared`.

    Skips the normalising, and so must only ever be handed sequences that have
    been through it — with the *same* language, or the two sides are folded by
    different rules and the number means nothing.
    """
    longest = max(len(a), len(b))
    if longest == 0:
        return 0.0
    cutoff = int(ceiling * longest) if ceiling is not None else None
    return _levenshtein(a, b, cutoff) / longest


def symbol_counts(phonemes: list[str]) -> Counter[str]:
    """How many of each symbol a pronunciation has, for `cannot_be_within`.

    Built once per lexicon entry by the caller that scans one, for the same
    reason `prepared` exists: the arithmetic is cheap and doing it per
    comparison is not.
    """
    return Counter(phonemes)


def cannot_be_within(
    a: list[str],
    b: list[str],
    ceiling: float,
    counts_a: Counter[str] | None = None,
    counts_b: Counter[str] | None = None,
) -> bool:
    """Whether two sequences are certainly further apart than `ceiling`.

    A *sound* prefilter, and the word is load-bearing: it may only ever say
    "certainly not", never "probably not". Levenshtein is at least the
    difference in length, because every extra symbol costs at least one edit, so

        distance >= abs(len(a) - len(b)) / max(len(a), len(b))

    and anything for which that lower bound already exceeds the ceiling can be
    skipped without computing the real distance. Nothing inside the band is ever
    discarded by it.

    It replaces a prefilter that was **not** sound and quietly cost real answers.
    That one asked whether two pronunciations shared a first or last phoneme,
    on the reasoning that a pun keeping neither edge is not recoverable — which
    reads well and is false. German `Glas` and `klar` share neither edge and sit
    at exactly 0.500, inside the default band; the salon sign `Ganz Glas` was
    unreachable for that reason alone, and the generator instead offered `Ganz
    klarer`, an inflection. The lesson is the one the house rules already state
    about guards: it encoded an answer someone found plausible rather than a
    rule that is true.
    """
    longest = max(len(a), len(b))
    if longest == 0:
        return False
    allowed = ceiling * longest
    if abs(len(a) - len(b)) > allowed:
        return True
    if counts_a is None or counts_b is None:
        return False
    # A second sound bound, and much the tighter of the two. Every symbol one
    # side has and the other lacks must be inserted, deleted or substituted;
    # a substitution repairs one surplus on each side at once, so the number of
    # edits is at least half the total surplus. Two words of the same length
    # sharing no symbols are `2n/2 = n` edits apart, which is exactly right.
    #
    # This is what makes an honest prefilter affordable: on German it takes the
    # comparisons for a two-word phrase from 69,090 to a fraction of that, with
    # no candidate inside the band discarded, because the bound can only ever
    # under-estimate the distance.
    #
    # Summed by hand rather than with `Counter` arithmetic. `counts_a - counts_b`
    # reads better and allocates two new Counters per candidate, which profiling
    # showed costing more than the edit distances it was there to avoid: 0.30s of
    # a 0.70s call, against 0.15s for the 17,875 comparisons that survive it.
    surplus = 0
    for symbol, count in counts_a.items():
        surplus += abs(count - counts_b.get(symbol, 0))
    for symbol, count in counts_b.items():
        if symbol not in counts_a:
            surplus += count
    return surplus / 2 > allowed


__all__ = [
    "ARPABET_TO_IPA",
    "CROSS_LINGUAL",
    "EQUIVALENT",
    "across_languages",
    "bare_phonemes",
    "cannot_be_within",
    "distance_prepared",
    "fold_equivalents",
    "phoneme_distance",
    "prepared",
    "symbol_counts",
    "to_ipa",
]
