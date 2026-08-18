"""Generators for larding. Both must yield (text, params) pairs.

`satisfying()` builds a source of unique one-word sentences, then interleaves a
lard between each pair — exactly the alternation the checker verifies, with lard
content ("lard1.", "lard2.", …) that can never collide with a source sentence
since source words are drawn from a purely alphabetic alphabet and lards always
carry a digit. `violating()` reuses at least two source sentences unlarded, which
always breaks the alternation since `expected_length = 2N - 1 > N` once `N >= 2`.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def _sentences(min_size: int, max_size: int) -> st.SearchStrategy[list[str]]:
    return st.lists(_WORD, min_size=min_size, max_size=max_size, unique=True)


def satisfying() -> CaseStrategy:
    def build(words: list[str]) -> tuple[str, dict[str, object]]:
        source_sentences = [f"{w}." for w in words]
        source = " ".join(source_sentences)
        parts = [source_sentences[0]]
        for index, sentence in enumerate(source_sentences[1:], start=1):
            parts.append(f"lard{index}.")
            parts.append(sentence)
        return " ".join(parts), {"source": source}

    return _sentences(1, 5).map(build)


def violating() -> CaseStrategy:
    def build(words: list[str]) -> tuple[str, dict[str, object]]:
        source = " ".join(f"{w}." for w in words)
        return source, {"source": source}

    return _sentences(2, 5).map(build)
