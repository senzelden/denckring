"""English part-of-speech tagging for denckring.

Installing this package adds the `pos` capability to the English pack, which is
what `verbless_prose` and `homosyntaxism` need and what nothing in core can
supply: telling a finite verb from a participle is a judgement about a word in
its sentence, and every other English capability here answers about a word on its
own (ADR 0045).

Unlike the syllable capabilities there is no heuristic tier for this one to
replace. A tagger is a model whatever data it is trained on, so the honesty lives
per token instead: `PosTag.known` says whether the form appeared in the training
data at all, and a procedure reporting a violation on a word where it did not
must say so in the violation.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Sequence
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from denckring_en_data import EnglishDataPack

from denckring.core.protocol import PosTag, VerbForm
from denckring.lang.base import POS
from denckring_en_pos.perceptron import Tagger

TAGGER_PATH = Path(str(files("denckring_en_pos") / "data" / "tagger.json.gz"))

__version__ = "0.3.1"

#: UD's `VerbForm` values as they appear in the trained labels. A table and not a
#: `cast` on whatever string the model emits: the labels come from a shipped file,
#: and a model rebuilt against a future treebank that introduced a new value would
#: otherwise widen `PosTag.verb_form` past its own type in silence.
_VERB_FORMS: dict[str, VerbForm | None] = {
    "-": None,
    "Fin": "Fin",
    "Part": "Part",
    "Inf": "Inf",
    "Ger": "Ger",
    "Sup": "Sup",
    "Conv": "Conv",
}


@lru_cache(maxsize=1)
def tagger() -> Tagger:
    """The trained model, read once.

    Cached because the table is a megabyte of JSON and a procedure tags one
    sentence at a time: reading it per call would make the cost of checking a
    paragraph quadratic in nothing.
    """
    raw = json.loads(gzip.decompress(TAGGER_PATH.read_bytes()).decode("utf-8"))
    return Tagger(
        weights=raw["weights"],
        tagdict=raw["tagdict"],
        classes=raw["classes"],
        vocabulary=frozenset(raw["vocabulary"]),
    )


class EnglishPosPack(EnglishDataPack):
    """English with a part-of-speech reading. Composed in by `denckring_en_data.pack`."""

    capabilities: ClassVar[frozenset[str]] = EnglishDataPack.capabilities | {POS}
    data_distributions: ClassVar[tuple[str, ...]] = (
        *EnglishDataPack.data_distributions,
        "denckring-en-pos",
    )

    def pos_tags(self, words: Sequence[str]) -> list[PosTag]:
        if not words:
            return []
        model = tagger()
        tags: list[PosTag] = []
        for word, label in zip(words, model.tag(words), strict=True):
            upos, _, verb_form = label.partition("|")
            tags.append(
                PosTag(
                    upos=upos,
                    verb_form=_VERB_FORMS[verb_form],
                    known=word.lower() in model.vocabulary,
                )
            )
        return tags


__all__ = ["TAGGER_PATH", "EnglishPosPack", "__version__", "tagger"]
