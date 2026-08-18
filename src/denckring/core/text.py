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

    Built on `splitlines`, the same as `line_spans`, so a blank line ending in
    `\\r\\n` closes a paragraph exactly as one ending in `\\n` does — splitting
    on the literal string `"\\n\\n"` would miss that.

    Unlike `line_spans`, this strips the surrounding whitespace of each block
    rather than keeping the original text: a paragraph's first and last lines
    can carry leading or trailing space that is not part of any line's own
    content, so the offset is rebased to the first non-whitespace character
    and the text returned has none. It now has three callers, two of which
    work in lines and offsets of their own — the offset this function returns
    is a stanza's or block's start, not necessarily the start of a line within
    it, and a caller measuring within the block must rebase against it.
    """
    spans: list[tuple[int, str]] = []
    group_start: int | None = None
    group_end = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if stripped.strip():
            if group_start is None:
                group_start = offset
            group_end = offset + len(stripped)
        elif group_start is not None:
            block = text[group_start:group_end]
            content = block.strip()
            spans.append((group_start + block.index(content[0]), content))
            group_start = None
        offset += len(line)
    if group_start is not None:
        block = text[group_start:group_end]
        content = block.strip()
        spans.append((group_start + block.index(content[0]), content))
    return spans
