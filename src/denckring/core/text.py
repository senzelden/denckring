"""Offset-preserving text helpers. Violations need character offsets."""

from __future__ import annotations

from denckring.core.protocol import LanguagePack


def letter_spans(text: str, pack: LanguagePack, *, fold: bool = True) -> list[tuple[int, str]]:
    """Every alphabetic character as `(offset, letter)`, lower-cased.

    With `fold` set, diacritics are stripped and `ß` expands to `ss`, so one
    source character can yield several letters sharing its offset. Without it,
    only case is normalised — `ä` stays `ä`.
    """
    spans: list[tuple[int, str]] = []
    for offset, ch in enumerate(text):
        if not ch.isalpha():
            continue
        letters = pack.fold_diacritics(ch) if fold else ch.lower()
        spans.extend((offset, letter) for letter in letters if letter.isalpha())
    return spans


def word_spans(text: str, pack: LanguagePack) -> list[tuple[int, str]]:
    """Every word as `(offset, word)`, unfolded."""
    return pack.word_spans(text)


def line_spans(text: str) -> list[tuple[int, str]]:
    """Every non-blank line as `(offset, line)`, keeping the original text."""
    spans: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if stripped.strip():
            spans.append((offset, stripped))
        offset += len(line)
    return spans


def paragraph_spans(text: str) -> list[tuple[int, str]]:
    """Every non-blank paragraph as `(offset, text)`, split on blank lines.

    A serial lipogram's parts are sections, not lines — Tryphiodorus wrote
    twenty-four books — so the unit has to be able to hold more than one line.
    """
    spans: list[tuple[int, str]] = []
    offset = 0
    for block in text.split("\n\n"):
        stripped = block.strip()
        if stripped:
            spans.append((offset + block.index(stripped[0]), stripped))
        offset += len(block) + 2
    return spans
