"""The tagger's feature set and inference, shared with the build script.

`scripts/build_tagger.py` imports `features` from here rather than defining its
own copy. That is the point of the module existing: a tagger whose training and
inference features drift apart does not fail, it quietly gets worse, and no test
of either half alone can see it. The build script is the only code in this
workspace that imports from `src/` into `scripts/`, and it does so within its
own distribution.

The model is an averaged perceptron over the feature set Honnibal published for
`textblob-aptagger` and later `spaCy`'s first tagger — the standard cheap tagger,
chosen because it is pure Python at inference time and its weights are a table
that can be shipped, verified and diffed like every other dataset here (ADR 0045).
"""

from __future__ import annotations

from collections.abc import Sequence

#: Sentence boundary markers, so a feature reading past either end of the
#: sentence gets a value rather than being dropped. Angle brackets cannot
#: collide with a real token: `word_spans` yields letters only.
START = "<s>"
END = "</s>"


def features(index: int, word: str, context: Sequence[str], prev: str, prev2: str) -> list[str]:
    """The feature strings for one token.

    `context` is the whole sentence already lower-cased; `prev` and `prev2` are
    the two tags guessed to the left, which is what makes this a sequence model
    rather than a per-word lookup.

    Deliberately no normalisation of digits or hyphens. denckring tags the
    `word_spans` stream, which is letters and internal apostrophes only — there
    are no bare numerals or punctuation tokens for a normaliser to fold.
    """
    lower = word.lower()
    shape = "X" if word[:1].isupper() else "x"
    if any(ch.isdigit() for ch in word):
        shape += "d"
    return [
        "bias",
        f"suf3 {lower[-3:]}",
        f"suf2 {lower[-2:]}",
        f"suf1 {lower[-1:]}",
        f"pre1 {lower[:1]}",
        f"shape {shape}",
        f"w {lower}",
        f"t-1 {prev}",
        f"t-2 {prev2}",
        f"t-1t-2 {prev} {prev2}",
        f"w-1 {context[index - 1] if index else START}",
        f"w-2 {context[index - 2] if index > 1 else START}",
        f"w+1 {context[index + 1] if index + 1 < len(context) else END}",
        f"w+2 {context[index + 2] if index + 2 < len(context) else END}",
        f"t-1 w {prev} {lower}",
    ]


class Tagger:
    """Inference over a trained model. Training lives in the build script."""

    def __init__(
        self,
        weights: dict[str, dict[str, float]],
        tagdict: dict[str, str],
        classes: Sequence[str],
        vocabulary: frozenset[str],
    ) -> None:
        self.weights = weights
        self.tagdict = tagdict
        #: Sorted, and the tie-break below depends on it: two labels reaching the
        #: same score must resolve the same way on every machine and every run,
        #: because a procedure's verdict is derived from the answer.
        self.classes = sorted(classes)
        self.vocabulary = vocabulary

    def _predict(self, feats: Sequence[str]) -> str:
        scores: dict[str, float] = {}
        for feat in feats:
            row = self.weights.get(feat)
            if row is None:
                continue
            for label, weight in row.items():
                scores[label] = scores.get(label, 0.0) + weight
        if not scores:
            return self.classes[-1]
        # Score first, then the label itself: `max` keeps the first maximum it
        # sees, so without the second key the winner among equals would depend on
        # dict order, which is insertion order, which is feature order.
        return max(self.classes, key=lambda label: (scores.get(label, 0.0), label))

    def tag(self, words: Sequence[str]) -> list[str]:
        """One `"UPOS|VerbForm"` label per token, left to right.

        A joint label rather than two models: `VerbForm` is only ever asked of a
        verb, and a pair of independently-argmaxed models can return a nominal
        tag carrying a finite verb form, which is a reading no annotation has.
        """
        out: list[str] = []
        prev, prev2 = START, START
        context = [word.lower() for word in words]
        for index, word in enumerate(words):
            guess = self.tagdict.get(context[index])
            if guess is None:
                guess = self._predict(features(index, word, context, prev, prev2))
            out.append(guess)
            prev2, prev = prev, guess
        return out
