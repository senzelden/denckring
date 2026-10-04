"""Generators for mesostic."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_WORD = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)


def _spine_from(words: list[str]) -> str:
    """The spine that makes `words`, one per line in order, a valid mesostic
    reading of themselves: letter `i` of the spine is word `i`'s own first
    letter, which is trivially *in* that word."""
    return "".join(word[0] for word in words)


def satisfying() -> CaseStrategy:
    """The source has one word more than the reading takes, so the reading is never
    a copy, which the row refuses by default since 0.4.0 (ADR 0055)."""
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (
            "\n".join(ws),
            {"source": " ".join([*ws, "zzzzzz"]), "spine": _spine_from(ws)},
        )
    )


def violating() -> CaseStrategy:
    """An extra line appended after a valid reading cannot be in the source, once
    the cursor has advanced past every real word — the same trick `diastic` uses."""
    return st.lists(_WORD, min_size=1, max_size=6).map(
        lambda ws: (
            "\n".join([*ws, "zzzzzz"]),
            {"source": " ".join(ws), "spine": _spine_from(ws)},
        )
    )
