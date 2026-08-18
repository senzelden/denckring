"""Generators for the double dactyl."""

from hypothesis import strategies as st

from strategies import CaseStrategy

#: Verified against CMUdict before use — see the plan's Step 5.
#: `100`, three syllables exact: two of these tile a `100100` line.
_DACTYL = st.sampled_from(["murmuring", "beautiful", "carefully", "wonderful"])

#: `?`, one syllable exact — free, so it takes whatever beat a `1001` line's
#: last position needs.
_FREE = st.sampled_from(["song", "light", "stone", "sea"])

#: Ordinary monosyllabic prose, also `?` — reused for the wrong-metre shape.
_PROSE = st.sampled_from(["and", "the", "of", "in"])

#: CMUdict gives `vulnerability` the pattern `?00100` — six syllables, exact
#: — and `?00100` fits `100100` through its free first syllable. The one
#: candidate verified to work; do not substitute a word whose pattern equals
#: `100100`, because none exists (CMUdict marks the fourth syllable of such a
#: word as secondary stress, which this pack renders as `?`, not `1`).
_SIX_SYLLABLE_WORD = "vulnerability"

#: Two dactyls: `100` + `100` = `100100`.
_DOUBLE_DACTYL_LINE = st.tuples(_DACTYL, _DACTYL).map(" ".join)

#: A dactyl closed by a free monosyllable: `100` + `?` fits `1001`.
_CLOSE_LINE = st.tuples(_DACTYL, _FREE).map(" ".join)


def satisfying() -> CaseStrategy:
    """Eight lines matching PATTERNS, with one of the three double-dactyl
    lines of the second quatrain (index 4, 5 or 6) replaced by a single
    six-syllable word. The slot is drawn rather than fixed, so satisfying()
    exercises all three positions the checkable clause allows rather than
    only the first."""
    body: CaseStrategy = st.tuples(
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _CLOSE_LINE,
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        st.integers(min_value=0, max_value=2),
        _CLOSE_LINE,
    ).map(_place_double_dactylic_word)
    return body


def _place_double_dactylic_word(
    parts: tuple[str, str, str, str, str, str, int, str],
) -> tuple[str, dict[str, object]]:
    line1, line2, line3, line4, dactyl_a, dactyl_b, slot, line8 = parts
    second_dactyls = [dactyl_a, dactyl_b]
    second_dactyls.insert(slot, _SIX_SYLLABLE_WORD)
    lines = [line1, line2, line3, line4, *second_dactyls, line8]
    return "\n".join(lines), {}


def violating() -> CaseStrategy:
    """Three shapes, so `wrong_line_count`, `no_double_dactylic_word` and the
    metre's own `wrong_line_length` are all reached: the wrong number of
    lines, eight lines of the right metre whose second quatrain never
    resolves to a single six-syllable word, and eight lines of ordinary
    monosyllabic prose that does not scan as double dactyls at all."""
    wrong_count: CaseStrategy = st.lists(_DOUBLE_DACTYL_LINE, min_size=1, max_size=7).map(
        lambda ls: ("\n".join(ls), {})
    )
    missing_word: CaseStrategy = st.tuples(
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _CLOSE_LINE,
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _DOUBLE_DACTYL_LINE,
        _CLOSE_LINE,
    ).map(lambda ls: ("\n".join(ls), {}))
    wrong_metre: CaseStrategy = st.lists(_PROSE, min_size=8, max_size=8).map(
        lambda ws: ("\n".join(ws), {})
    )
    return st.one_of(wrong_count, missing_word, wrong_metre)
