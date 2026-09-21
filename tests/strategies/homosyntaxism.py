"""Generators for homosyntaxism.

Unlike the letter rows, a case here cannot be built by transforming random
letters: the verdict comes from a tagger, so both texts have to be real English
in a frame the tagger reads the same way twice. The pools below are measured
rather than guessed — all 17x12x17 fillings of the frame
`The <noun> <verb> the <noun>` tag exactly `DET NOUN VERB DET NOUN`, which is
what lets `satisfying()` promise a satisfied case without re-running the tagger
to check. `garden` was in the noun pool and is not: in the first slot it tags
ADJ, and one such word is enough to make a case that should pass fail.
"""

from hypothesis import strategies as st

from strategies import CaseStrategy

_NOUNS = (
    "boy",
    "girl",
    "man",
    "woman",
    "dog",
    "cat",
    "horse",
    "bird",
    "book",
    "door",
    "window",
    "letter",
    "bread",
    "table",
    "river",
    "child",
    "teacher",
)
_VERBS = (
    "opened",
    "closed",
    "carried",
    "watched",
    "painted",
    "pushed",
    "pulled",
    "wanted",
    "needed",
    "followed",
    "kicked",
    "washed",
)

#: One frame's worth of a case: for each of the three open-class slots, the
#: word the source puts there and the word the rewriting puts there.
Clause = tuple[tuple[str, str], tuple[str, str], tuple[str, str]]


def _distinct(pool: tuple[str, ...]) -> st.SearchStrategy[tuple[str, str]]:
    """A (source word, replacement) pair that are not the same word.

    Distinct because all three slots are open class, where the row's "new
    words" clause bites: drawing the same noun twice would build a
    `repeated_word` violation into a case meant to satisfy.
    """
    return st.tuples(st.sampled_from(pool), st.sampled_from(pool)).filter(
        lambda pair: pair[0] != pair[1]
    )


_CLAUSE = st.tuples(_distinct(_NOUNS), _distinct(_VERBS), _distinct(_NOUNS))


def _side(clauses: list[Clause], which: int) -> str:
    return " ".join(f"The {n[which]} {v[which]} the {o[which]}." for n, v, o in clauses)


def satisfying() -> CaseStrategy:
    return st.lists(_CLAUSE, min_size=1, max_size=3).map(
        lambda clauses: (_side(clauses, 1), {"source": _side(clauses, 0)})
    )


def violating() -> CaseStrategy:
    """A whole extra sentence appended to the text guarantees a trailing
    `extra_words` violation whatever the source says, because the text then has
    more tokens than the source has positions to match them against. Appending
    a bare word to the last sentence would not do: it would change how that
    sentence's own words tag, and the case could then fail for a rule other
    than the one it is named for."""
    return st.lists(_CLAUSE, min_size=1, max_size=3).map(
        lambda clauses: (
            f"{_side(clauses, 1)} The bird watched the cat.",
            {"source": _side(clauses, 0)},
        )
    )
