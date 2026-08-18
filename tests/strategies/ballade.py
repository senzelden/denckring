"""Generators for ballade.

A valid instance cannot be generated blind — the three rhyme families have to be
held constant across all three stanzas, every non-refrain line on its own word,
and the refrain repeated verbatim four times — so these sample verified texts,
as `rhyme_royal` does for the same reason.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

CONFORMING = """a cat can climb a tall old tree
the dog will run and play all day
the bird will fly out to the sea
the sun will shine and light the way
the sky will clear by first of may
the wall was built of gray old stone
the birds will call what they all say
until the northern wind has blown
the clock will chime at half past three
the boys will laugh and run to play
a fish will leap and swim so free
the guests will come and wish to stay
the storm clouds turn both dark and gray
the barn stood dark and stayed alone
the goats will roam and love to stray
until the northern wind has blown
he holds the door shut with a key
the trees will bend then start to sway
the priest will grant the poor his plea
the child will shape the wet soft clay
the light comes down in one long ray
the truth at last to all was known
the hens will rest then soon they lay
until the northern wind has blown
the men will come at dusk to pay
the corn stood tall for it had grown
the ships will sail out past the bay
until the northern wind has blown"""

#: The refrain broken at its final occurrence.
VIOLATING = "\n".join([*CONFORMING.splitlines()[:27], "a different closing line entirely"])

PARAMS: dict[str, object] = {}


def satisfying() -> CaseStrategy:
    return st.just((CONFORMING, dict(PARAMS)))


def violating() -> CaseStrategy:
    return st.just((VIOLATING, dict(PARAMS)))
