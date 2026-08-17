"""Local corpus files, offered to the bench as a picker.

A corpus reaches a procedure through `source` as text, and the ones worth
testing against are large — the Jean Paul excerpts run to 166KB for ten
fascicle volumes, which is not something to paste into a textarea. So the
explorer reads them off disk instead.

Nothing is bundled and nothing is copied. The directory is named by
`DENCKRING_CORPORA` and defaults to ~/corpora; ADR 0020 decided that a corpus
belongs to whoever assembled it, and pointing at a folder keeps it that way —
the file stays where the reader put it, outside this repository.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

#: Big enough for the whole Würzburg export, small enough that a stray log file
#: cannot wedge the page.
MAX_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class Corpus:
    """One file on disk, described well enough to choose between them."""

    name: str
    path: str
    entries: int
    headwords: int
    domains: list[str]
    #: Which register the Witz reading should be written in. Declared by the
    #: corpus itself, because it is a property of the material: Jean Paul's
    #: excerpts want his prose, arXiv abstracts want ours.
    style: str = "modern"


def directory() -> Path:
    return Path(os.environ.get("DENCKRING_CORPORA", Path.home() / "corpora")).expanduser()


def _describe(path: Path) -> Corpus | None:
    """Read a corpus far enough to label it, or skip it.

    Uses the library's own parser rather than a second reading of the format:
    if `denckring` cannot load the file, the explorer has no business offering
    it, and the two can never disagree about what a corpus is.
    """
    from denckring.core import corpus as corpora
    from denckring.core.errors import MalformedCorpus

    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        parsed = corpora.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, MalformedCorpus):
        return None
    try:
        declared = json.loads(path.read_text(encoding="utf-8")).get("style", "modern")
    except (OSError, json.JSONDecodeError, AttributeError):
        declared = "modern"
    return Corpus(
        name=parsed.name,
        path=str(path),
        entries=len(parsed.entries()),
        headwords=len(parsed.headwords()),
        domains=parsed.domains(),
        style=str(declared),
    )


def available() -> list[Corpus]:
    """Every readable corpus in the directory, by filename."""
    root = directory()
    if not root.is_dir():
        return []
    found = [_describe(path) for path in sorted(root.glob("*.json"))]
    return [corpus for corpus in found if corpus is not None]


def load(path: str) -> tuple[str, str]:
    """The text of one corpus, refusing anything outside the directory.

    The path arrives from a form, so it is checked against the directory rather
    than trusted — the explorer binds to localhost, but reading arbitrary files
    off the disk because a query parameter said so is still not something to
    leave open.
    """
    root = directory().resolve()
    try:
        target = Path(path).resolve()
        if not target.is_relative_to(root):
            return "", "That file is outside the corpus directory."
        return target.read_text(encoding="utf-8"), ""
    except (OSError, UnicodeDecodeError, ValueError):
        return "", "That corpus could not be read."


def headwords_of(text: str) -> list[str]:
    """Every headword the corpus files entries under, for the picker."""
    from denckring.core import corpus as corpora
    from denckring.core.errors import MalformedCorpus

    try:
        return corpora.parse(text).headwords()
    except (MalformedCorpus, json.JSONDecodeError):
        return []
