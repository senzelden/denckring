"""Corpora: partitioned collections a procedure draws from.

The third shape this package needs. A device is a product over closed rings and
a figure is a combination over one alphabet; both are finite and shipped. A
corpus is external, open-ended, and belongs to whoever assembled it — so nothing
here ships one. The package carries the loader; the reader supplies the reading.

Jean Paul's excerpt books are the case that forces this. His notebook titled
*Ideenwürfeln* indexes them by headword, and the work is to force distant
material together under one word until a likeness appears. The headword is a
collision chamber, and the collision cannot be manufactured from anything the
package could ship.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from denckring.core.errors import MalformedCorpus

__all__ = ["Corpus", "Entry", "InMemoryCorpus", "MalformedCorpus", "parse"]


@dataclass(frozen=True)
class Entry:
    """One excerpt, and whatever is known about where it sits."""

    text: str
    id: str | None = None
    #: The field it was drawn from — antiquity, anatomy, entomology. Often
    #: unknown, and the drawing procedures must cope with that rather than
    #: pretend otherwise.
    domain: str | None = None
    #: The excerptor's own citation, not the edition's.
    source: str | None = None
    headwords: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class Corpus(Protocol):
    """A collection that can be asked for entries, by headword or entire."""

    def entries(self, headword: str | None = None) -> list[Entry]: ...

    def headwords(self) -> list[str]: ...

    def domains(self) -> list[str]: ...


class InMemoryCorpus:
    """A corpus held as a list. What tests use, and what parsers build."""

    def __init__(self, entries: list[Entry], name: str = "in-memory") -> None:
        self._entries = list(entries)
        self.name = name

    def entries(self, headword: str | None = None) -> list[Entry]:
        if headword is None:
            return list(self._entries)
        wanted = headword.casefold()
        return [
            entry
            for entry in self._entries
            if any(word.casefold() == wanted for word in entry.headwords)
        ]

    def headwords(self) -> list[str]:
        return sorted({word for entry in self._entries for word in entry.headwords})

    def domains(self) -> list[str]:
        return sorted({entry.domain for entry in self._entries if entry.domain})

    def __len__(self) -> int:
        return len(self._entries)


def parse(text: str) -> InMemoryCorpus:
    """Read a corpus from JSON, or from plain text as one entry per line.

    Two JSON shapes are accepted. The general one keys entries under `entries`
    with `text`, `id`, `domain`, `source` and `headwords`. The other is the shape
    the Würzburg Jean-Paul edition's export takes — `eintraege`, each with `id`
    and `t` — which is read because that is what a reader of this procedure is
    most likely to have, not because the data travels with the package.
    """
    stripped = text.strip()
    if not stripped:
        raise MalformedCorpus("it is empty")
    if not stripped.startswith("{") and not stripped.startswith("["):
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        return InMemoryCorpus([Entry(text=line) for line in lines], name="plain text")

    try:
        raw: Any = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise MalformedCorpus(f"it is not valid JSON ({exc.msg})") from exc

    if isinstance(raw, list):
        rows, name = raw, "json list"
    elif "entries" in raw:
        rows, name = raw["entries"], str(raw.get("name", "json"))
    elif "eintraege" in raw:
        rows, name = raw["eintraege"], str(raw.get("quelle", "json"))
    else:
        raise MalformedCorpus("it has neither an 'entries' nor an 'eintraege' key")

    entries = []
    for row in rows:
        if isinstance(row, str):
            entries.append(Entry(text=row))
            continue
        body = row.get("text") or row.get("t") or ""
        entries.append(
            Entry(
                text=str(body),
                id=row.get("id"),
                domain=row.get("domain") or row.get("fach"),
                source=row.get("source") or row.get("quelle"),
                headwords=tuple(row.get("headwords") or row.get("stichworte") or ()),
            )
        )
    if not entries:
        raise MalformedCorpus("it holds no entries")
    return InMemoryCorpus(entries, name=name)
