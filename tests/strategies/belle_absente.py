"""Generators for belle_absente. `satisfying` and `violating` are the module contract."""

import string

from hypothesis import strategies as st

from strategies import CaseStrategy

ALPHABET = string.ascii_lowercase


def _line_without(letter: str) -> str:
    """Every letter but one, which is exactly what each line must contain."""
    return " ".join(ch for ch in ALPHABET if ch != letter)


def _poem(name: str) -> tuple[str, dict[str, object]]:
    letters = [ch for ch in name if ch.isalpha()]
    return "\n".join(_line_without(ch) for ch in letters), {"name": name}


def satisfying() -> CaseStrategy:
    return st.text(alphabet=ALPHABET, min_size=1, max_size=5).map(_poem)


def violating() -> CaseStrategy:
    """Put the forbidden letter back into the first line."""

    def spoil(pair: tuple[str, str]) -> tuple[str, dict[str, object]]:
        name, _ = pair[0], pair[1]
        text, params = _poem(name)
        first = next(ch for ch in name if ch.isalpha())
        return first + text, params

    return st.tuples(
        st.text(alphabet=ALPHABET, min_size=1, max_size=5),
        st.just(""),
    ).map(spoil)
