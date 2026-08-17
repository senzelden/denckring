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
    """Spoil a satisfying poem one of three ways, each its own violation kind."""

    def spoil_forbidden_letter(name: str) -> tuple[str, dict[str, object]]:
        """Put the forbidden letter back into the first line."""
        text, params = _poem(name)
        first = next(ch for ch in name if ch.isalpha())
        return first + text, params

    def spoil_missing_letter(name: str) -> tuple[str, dict[str, object]]:
        """Drop a required letter out of the first line."""
        text, params = _poem(name)
        lines = text.split("\n")
        first_letter = next(ch for ch in name if ch.isalpha())
        survivor = next(ch for ch in ALPHABET if ch != first_letter)
        lines[0] = " ".join(ch for ch in ALPHABET if ch not in (first_letter, survivor))
        return "\n".join(lines), params

    def spoil_wrong_line_count(name: str) -> tuple[str, dict[str, object]]:
        """Add an extra line the name does not call for."""
        text, params = _poem(name)
        return text + "\n" + _line_without("a"), params

    return st.text(alphabet=ALPHABET, min_size=1, max_size=5).flatmap(
        lambda name: st.sampled_from(
            [
                spoil_forbidden_letter(name),
                spoil_missing_letter(name),
                spoil_wrong_line_count(name),
            ]
        )
    )
