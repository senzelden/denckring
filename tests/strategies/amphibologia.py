"""Generators for amphibologia.

Sampled rather than drawn blind: whether a word is polysemous is a fact about a
dictionary, not something a random string can be arranged to satisfy.
"""

from typing import Any

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING: list[tuple[str, dict[str, Any]]] = [
    ("A Cut Above", {"domain": "hair"}),
    ("Shear Delight", {"domain": "hair"}),
    ("Bread and butter", {"domain": "bakery"}),
]

#: (text, params, the rule it must trip).
VIOLATING: list[tuple[str, dict[str, Any], str]] = [
    ("Nothing relevant here", {"domain": "hair"}, "no_trade_word"),
    ("A xylophone above", {"domain_words": ["xylophone"]}, "unambiguous"),
]


def satisfying() -> CaseStrategy:
    return st.sampled_from(CONFORMING)


def violating() -> CaseStrategy:
    return st.sampled_from([(text, params) for text, params, _ in VIOLATING])
