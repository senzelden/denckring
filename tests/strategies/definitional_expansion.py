"""Generators for definitional_expansion.

Instances rest on lexicon membership and on a specific dictionary's actual prose, both
of which cannot be generated blind — a random string is almost never a word, and even a
random real word's gloss cannot be guessed — so these sample from fixed, verified text,
the same reason `n_plus_7`'s strategies do. Both texts below are `get_pack("en").glosses`
output, read verbatim.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SOURCE = "the garden was quiet"

# get_pack("en").glosses("garden")[1] and glosses("quiet")[0], read verbatim.
_GARDEN_GLOSS = "a plot of ground where plants are cultivated"
_QUIET_GLOSS = "characterized by an absence or near absence of agitation or activity"

_EXPANDED = f"the {_GARDEN_GLOSS} was {_QUIET_GLOSS}"
_ONE_LEFT_UNEXPANDED = f"the {_GARDEN_GLOSS} was quiet"


def satisfying() -> CaseStrategy:
    return st.just((_EXPANDED, {"source": _SOURCE}))


def violating() -> CaseStrategy:
    return st.just((_ONE_LEFT_UNEXPANDED, {"source": _SOURCE}))
