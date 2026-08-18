"""Generators for diastic."""

from hypothesis import strategies as st

from strategies import CaseStrategy

# Fixed length so every position 0..5 exists in every word: `_seed_from` reads
# `word[i]` for `i` up to 5 without needing a fallback for short words.
_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=6, max_size=6)


def _seed_from(words: list[str]) -> str:
    """The seed that makes `words`, taken in source order, a valid diastic
    reading of themselves: letter `i` of the seed is letter `i` of word `i`."""
    return "".join(word[i] for i, word in enumerate(words))


def satisfying() -> CaseStrategy:
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (" ".join(ws), {"source": " ".join(ws), "seed_phrase": _seed_from(ws)})
    )


def violating() -> CaseStrategy:
    """An extra word appended after a valid reading cannot be in the source,
    whatever the seed says, once the cursor has advanced past every real word."""
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (
            " ".join([*ws, "zzzzzz"]),
            {"source": " ".join(ws), "seed_phrase": _seed_from(ws)},
        )
    )
