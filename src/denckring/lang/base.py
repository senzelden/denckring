"""Capability constants and the shared pack implementation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import ClassVar

from denckring.core.errors import MissingCapability
from denckring.core.protocol import Lang

TOKENS = "tokens"
ALPHABET = "alphabet"
FOLD_DIACRITICS = "fold_diacritics"
LETTER_SHAPES = "letter_shapes"
SYLLABLES = "syllables"
NOUNS = "lexicon.nouns"

# Both apostrophes are intentional: real text uses the typographic one.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)  # noqa: RUF001

#: Stands in for the procedure name when a pack method is called directly rather
#: than through `BaseProcedure.check`, which knows what it is checking.
DIRECT_CALL = "<direct call>"


class BasePack:
    """Shared behaviour. A method whose capability is undeclared must raise."""

    lang: ClassVar[Lang]
    capabilities: ClassVar[frozenset[str]] = frozenset()
    word_re: ClassVar[re.Pattern[str]] = WORD_RE

    def tokenize(self, text: str) -> list[str]:
        return [word for _, word in self.word_spans(text)]

    def word_spans(self, text: str) -> list[tuple[int, str]]:
        return [(m.start(), m.group()) for m in self.word_re.finditer(text)]

    def fold_diacritics(self, ch: str) -> str:
        """Case-fold and strip combining marks.

        Case-folding rather than lower-casing, so that `ß` becomes `ss` — which
        means the result may be longer than one character, and callers must not
        assume otherwise.
        """
        decomposed = unicodedata.normalize("NFKD", ch.casefold())
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    def alphabet(self) -> str:
        raise MissingCapability(DIRECT_CALL, self.lang, ALPHABET)

    def vowels(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, ALPHABET)

    def ascenders(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)

    def descenders(self) -> frozenset[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, LETTER_SHAPES)

    def syllables(self, word: str) -> list[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, SYLLABLES)

    def nouns(self) -> Iterable[str]:
        raise MissingCapability(DIRECT_CALL, self.lang, NOUNS)
