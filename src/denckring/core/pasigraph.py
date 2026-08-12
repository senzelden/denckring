"""Numbered vocabularies: a word, a number, the same number in another tongue.

Kircher's *Polygraphia Nova* (1663) reduces five languages to one numbered
dictionary, so that a number stands for corresponding words in each. Writing
becomes arithmetic: look the word up, send the number, look it up again at the
other end.

What makes it worth implementing is not that it works but where it fails. A word
with no number cannot cross. Two words sharing a number arrive as one, and the
distinction between them is gone. A number with no entry in the target language
strands the sentence. Those losses are the interesting part, so they are counted
and reported rather than smoothed over.

No historical table ships. Kircher's vocabulary has not been transcribed into
anything machine-readable this project could verify, and inventing one would
make the checker check fiction.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from denckring.core.errors import MalformedTable


@dataclass(frozen=True)
class Table:
    """A numbered vocabulary across several languages."""

    #: number -> language -> word
    entries: dict[str, dict[str, str]]

    @property
    def languages(self) -> list[str]:
        return sorted({lang for row in self.entries.values() for lang in row})

    def number_for(self, word: str, lang: str) -> str | None:
        """The first number listing this word in this language."""
        folded = word.casefold()
        for number, row in self.entries.items():
            if row.get(lang, "").casefold() == folded:
                return number
        return None

    def word_at(self, number: str, lang: str) -> str | None:
        return self.entries.get(number, {}).get(lang)

    def collisions(self, lang: str) -> dict[str, list[str]]:
        """Words reachable from more than one number, and the numbers reaching them.

        This is where the vocabulary loses information. Two numbers arriving at
        one word means two distinct things in the sending language become the
        same thing on receipt, and nothing downstream can tell them apart again.
        """
        grouped: dict[str, list[str]] = {}
        for number, row in self.entries.items():
            word = row.get(lang)
            if word:
                grouped.setdefault(word.casefold(), []).append(number)
        return {word: numbers for word, numbers in grouped.items() if len(numbers) > 1}


def parse(text: str) -> Table:
    """Read a numbered vocabulary from JSON.

    Either `{"1": {"la": "deus", "de": "gott"}}` or the same under an `entries`
    key, so a table can carry its own provenance alongside the words.
    """
    stripped = text.strip()
    if not stripped:
        raise MalformedTable("it is empty")
    try:
        raw: Any = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise MalformedTable(f"it is not valid JSON ({exc.msg})") from exc
    if not isinstance(raw, dict):
        raise MalformedTable("it is not an object of numbered entries")
    rows = raw.get("entries", raw)
    if not isinstance(rows, dict) or not rows:
        raise MalformedTable("it holds no numbered entries")
    entries: dict[str, dict[str, str]] = {}
    for number, row in rows.items():
        if not isinstance(row, dict):
            raise MalformedTable(f"entry {number!r} is not a mapping of language to word")
        entries[str(number)] = {str(k): str(v) for k, v in row.items()}
    return Table(entries=entries)
