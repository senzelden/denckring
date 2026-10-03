"""The smallest unit a row's verdict is a verdict on (audit C2).

A consumer composing rows needs to know which ones judge each word alone: a text
joined from words a lipogram passes one at a time passes too, and one word it
fails fails the whole. denckring-bench learned this by checking a whole lexicon
word by word and bisecting violation offsets, and kept forty-four hand-written
reasons for it. A row says it here instead, and `tests/test_scope.py` holds every
claim to the checker.

A scope is a promise about texts built from units, not about every string:

- `word`: a text of words joined by spaces, line breaks or punctuation passes if
  and only if every word passes alone.
- `line`: a text of lines joined by line breaks passes if and only if every line
  passes alone.
- `sentence`: a text of sentences, each closed by `.`, `!` or `?` and joined by a
  space, passes if and only if every sentence passes alone.
- `text`: no such promise. The default, so a row that makes no claim makes no
  false one.

A word-scoped row is line- and sentence-scoped too, since a line or a sentence
is words. Line and sentence are not nested in each other, so a composite of
the two is `text`.

The scope can depend on parameters. A tautogram with its initial unset infers it
from the first word, so the verdict on any word depends on the text's first, and
the row is word-scoped only with `initial` stated.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

Scope = Literal["word", "line", "sentence", "text"]

#: Each scope, and what it promises.
SCOPES: dict[str, str] = {
    "word": (
        "A text of words joined by spaces, line breaks or punctuation passes if and only "
        "if every word passes alone."
    ),
    "line": (
        "A text of lines joined by line breaks passes if and only if every line passes alone."
    ),
    "sentence": (
        "A text of sentences, each closed by '.', '!' or '?' and joined by a space, passes "
        "if and only if every sentence passes alone."
    ),
    "text": "No unit smaller than the text is judged alone.",
}


def coarsest(scopes: Iterable[Scope]) -> Scope:
    """The scope every one of `scopes` keeps: what a text passing all of them has.

    Each row's promise holds of a unit at its own scope or any that contains it,
    so a text built of lines passes a word-scoped row and a line-scoped row line
    by line. Sentences can span lines, so a line-scoped row and a
    sentence-scoped one share no unit smaller than the text.
    """
    found = set(scopes)
    if found <= {"word"}:
        return "word"
    if found <= {"word", "line"}:
        return "line"
    if found <= {"word", "sentence"}:
        return "sentence"
    return "text"
