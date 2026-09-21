"""Generators for verbless_prose.

Both strategies compose whole sentences, not words, and join them with a full
stop. That is what makes them sound against a statistical tagger: the checker
groups on sentence punctuation and tags each group on its own, so a phrase that
checks clean alone still checks clean beside any other, and one carrying a finite
verb still carries it. Composing at the word level would hand the tagger contexts
nobody verified and make a failure here a fact about the draw rather than about
the checker.

Each phrase below was run through the checker singly before being listed. Two
candidates were dropped for failing that: `Fog everywhere, fog up the river` is
verbless and comes back with `fog` flagged, and `The dog barks` has a finite verb
and comes back satisfied. They are the row's measured error rate (ADR 0045), not
material for a property test.
"""

from hypothesis import strategies as st

from strategies import Case, CaseStrategy

_VERBLESS = st.sampled_from(
    [
        "Implacable November weather",
        "A cold night, and no moon",
        "Dogs in the mire, horses in the mud",
        "The Lord Chancellor in his High Court",
        "Gas looming through the fog in divers places",
        "A general infection of ill temper",
    ]
)

_FINITE = st.sampled_from(
    [
        "She walked home",
        "The gate was open",
        "He did not look back",
        "They have gone",
    ]
)


def _text(sentences: list[str]) -> Case:
    return (". ".join(sentences) + "." if sentences else "", {})


def satisfying() -> CaseStrategy:
    return st.lists(_VERBLESS, max_size=5).map(_text)


def violating() -> CaseStrategy:
    # The finite clause is always present, and always its own sentence: an empty
    # draw would be an empty text, which `_report` scores vacuously satisfied.
    return st.tuples(st.lists(_VERBLESS, max_size=4), _FINITE).map(
        lambda pair: _text([*pair[0], pair[1]])
    )
