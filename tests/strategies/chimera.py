"""Generators for chimera. Both must yield (text, params) pairs.

Like `homosyntaxism`, and unlike the letter rows, a case here cannot be built by
transforming random letters: the verdict comes from a tagger, so the frame, the
candidate and all three donors have to be real English in a frame the tagger
reads the same way every time. The pools below are measured rather than
guessed — all 8x18x11x18 = 35,640 fillings of the frame
`The <adj> <noun> <verb> the <noun>.` tag exactly `DET ADJ NOUN VERB DET NOUN`,
with every token `known`. Three words were dropped by that measurement rather
than by taste: `quiet` and `thin` tag NOUN in the adjective slot often enough to
matter (180 and 234 fillings), and `closed` tags ADJ in three.

`_OUTSIDER` is the one noun kept out of every donor, so `violating()` can put a
word in the candidate that is a NOUN and is in no donor — a `not_from_donor`
violation by construction, which is the rule that case is named for. Building a
violation by appending words instead would fail on `extra_words`, a rule this
row shares with `homosyntaxism` and which says nothing about donors.
"""

from hypothesis import strategies as st

from strategies import Case, CaseStrategy

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
_ADJS = ("quick", "small", "cold", "heavy", "warm", "dark", "empty", "wide")

#: A noun in the measured pool that no donor is ever built from.
_OUTSIDER = "mountain"

#: One sentence's worth of the frame: adjective, subject, verb, object.
Filling = tuple[str, str, str, str]

_FILLING = st.tuples(
    st.sampled_from(_ADJS),
    st.sampled_from(_NOUNS),
    st.sampled_from(_VERBS),
    st.sampled_from(_NOUNS),
)


def _sentence(filling: Filling) -> str:
    adjective, subject, verb, obj = filling
    return f"The {adjective} {subject} {verb} the {obj}."


def _case(fillings: tuple[Filling, Filling, Filling, Filling], subject: str | None) -> Case:
    """A frame, three donors, and the candidate that refills the frame from them.

    `subject` overrides the noun drawn for the candidate's subject slot, which is
    how `violating()` plants a word no donor supplies.
    """
    frame, nouns, verbs, adjectives = fillings
    candidate = _sentence(
        (adjectives[0], subject or nouns[1], verbs[2], nouns[3]),
    )
    return (
        candidate,
        {
            "source": _sentence(frame),
            "nouns_from": _sentence(nouns),
            "verbs_from": _sentence(verbs),
            "adjectives_from": _sentence(adjectives),
        },
    )


def satisfying() -> CaseStrategy:
    return st.tuples(_FILLING, _FILLING, _FILLING, _FILLING).map(
        lambda fillings: _case(fillings, None)
    )


def violating() -> CaseStrategy:
    return st.tuples(_FILLING, _FILLING, _FILLING, _FILLING).map(
        lambda fillings: _case(fillings, _OUTSIDER)
    )
