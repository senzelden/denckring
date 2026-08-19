"""Generators for definitional_literature.

Same reason as `definitional_expansion`'s strategies for sampling fixed text rather than
generating it: a random string is almost never a word, and a real word's dictionary
definition cannot be guessed — let alone a definition of the words of that definition.
Both texts below were produced by putting `the key` through the procedure with
`get_pack("en").glosses`, once and then twice.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_SOURCE = "the key"

# get_pack("en").glosses("key")[3], then the same treatment applied to its own words —
# of which only `crucial` resolves, taking its first sense.
_ONE_ROUND = "the something crucial for explaining"
_TWO_ROUNDS = (
    "the something of extreme importance; vital to the resolution of a crisis for explaining"
)


def satisfying() -> CaseStrategy:
    """One round and two rounds both satisfy the row, so both are drawn from."""
    return st.sampled_from([_ONE_ROUND, _TWO_ROUNDS]).map(lambda text: (text, {"source": _SOURCE}))


def violating() -> CaseStrategy:
    """The source unchanged: reachable in zero rounds, and zero is not repeating."""
    return st.just((_SOURCE, {"source": _SOURCE}))
