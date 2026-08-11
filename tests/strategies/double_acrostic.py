"""Generators for double_acrostic."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_MIDDLE = st.text(alphabet=_ALPHABET, max_size=4)


def satisfying() -> CaseStrategy:
    return st.lists(
        st.tuples(st.sampled_from(_ALPHABET), st.sampled_from(_ALPHABET), _MIDDLE),
        min_size=1,
        max_size=5,
    ).map(
        lambda rows: (
            "\n".join(a + mid + b for a, b, mid in rows),
            {"first": "".join(r[0] for r in rows), "last": "".join(r[1] for r in rows)},
        )
    )


def violating() -> CaseStrategy:
    return st.lists(_MIDDLE, min_size=2, max_size=4).map(
        lambda mids: (
            "\n".join("z" + m + "z" for m in mids),
            {"first": "a" * len(mids), "last": "a" * len(mids)},
        )
    )
