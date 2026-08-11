"""Generators for slenderizing."""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SOURCE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=14)


def satisfying() -> CaseStrategy:
    return _SOURCE.map(lambda source: (source.replace("r", ""), {"source": source, "deleted": "r"}))


def violating() -> CaseStrategy:
    return _SOURCE.map(lambda source: (source + "r", {"source": source, "deleted": "r"}))
