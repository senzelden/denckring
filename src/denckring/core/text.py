"""Offset-preserving text helpers. Violations need character offsets."""

from __future__ import annotations

import unicodedata

from denckring.core.errors import InvalidParams
from denckring.core.protocol import LanguagePack


def clusters(text: str) -> list[tuple[int, str]]:
    """Each base character with the combining marks that belong to it, at the
    base's offset.

    `ä` is one character in NFC and two in NFD, and a reader cannot tell which
    they have — macOS filenames are NFD, most editors write NFC. Walking the
    string character by character therefore reads the same word two different
    ways, and the mark, which is `Mn` rather than alphabetic, is the half that
    gets dropped.

    A mark with no base before it — a text beginning with one — belongs to
    nothing and is returned on its own, to be discarded by the `isalpha` test in
    the caller rather than silently attached to whatever follows it.
    """
    clusters: list[tuple[int, str]] = []
    for offset, ch in enumerate(text):
        if unicodedata.combining(ch) and clusters:
            index, base = clusters[-1]
            clusters[-1] = (index, base + ch)
        else:
            clusters.append((offset, ch))
    return clusters


def letter_spans(text: str, pack: LanguagePack, *, fold: bool = True) -> list[tuple[int, str]]:
    """Every alphabetic character as `(offset, letter)`, lower-cased.

    With `fold` set, diacritics are stripped and `ß` expands to `ss`, so one
    source character can yield several letters sharing its offset. Without it,
    only case is normalised — `ä` stays `ä`.

    That last promise is why this reads clusters rather than characters. A
    decomposed `ä` is `a` followed by U+0308, and taking those one at a time
    keeps the `a` — which is alphabetic — and drops the mark, which is not. So
    `fold=False` folded the diacritic it exists to preserve, and only for text
    that happened to arrive decomposed: `check("lipogram", "Bär",
    forbidden="a", fold_diacritics=False)` was satisfied on NFC and unsatisfied
    on NFD. Composing to NFC first is what makes a verdict a fact about the
    word rather than about how it was typed.

    The offset stays the base character's, so a `Violation` still points into
    the text the caller passed, whose length composing does not change.
    """
    spans: list[tuple[int, str]] = []
    for offset, cluster in clusters(text):
        if not cluster[0].isalpha():
            continue
        letters = (
            pack.fold_diacritics(cluster) if fold else unicodedata.normalize("NFC", cluster).lower()
        )
        spans.extend((offset, letter) for letter in letters if letter.isalpha())
    return spans


def fold_letter(ch: str, pack: LanguagePack, *, fold: bool) -> str:
    """One source character as the letters it contributes to a folded text.

    The parameter-side twin of `letter_spans`: that folds the text, and until
    this existed nothing folded the value compared against it, so `vowel="ä"`
    was unsatisfiable in German (ADR 0035). Multi-character under folding —
    `ß` gives `ss` — which is why `single_letter` exists beside it.

    The `isalpha` filter on the *result* is `letter_spans`' own, so the two
    sides of a comparison cannot disagree about which characters a fold
    contributes; a fold yielding no letters gives `""`. The filter on the
    *input* is not here, because a caller iterating a phrase decides for
    itself what counts as a character worth folding — `fold_target` is that
    caller, and it applies it.
    """
    return "".join(
        letter for letter in (pack.fold_diacritics(ch) if fold else ch.lower()) if letter.isalpha()
    )


def fold_target(value: str, pack: LanguagePack, *, fold: bool) -> list[str]:
    """A multi-character parameter flattened the way the text side flattens it.

    Not one entry per source character: `ß` folds to two letters and the text
    side already spends two units on it, so a per-character expectation
    compared a two-letter `"ss"` against a one-character `got` (ADR 0035, D3).

    One function rather than one expression per checker. The ADR rejects
    per-checker folding as "five checkers, five chances to differ", and the
    acrostic pair had already proved it by diverging with one copy each —
    which was still true of this expression, copied three times, after the
    fix that cited it.
    """
    return [letter for ch in value if ch.isalpha() for letter in fold_letter(ch, pack, fold=fold)]


def single_letter(
    value: str,
    pack: LanguagePack,
    *,
    fold: bool,
    procedure_id: str,
    field: str,
    whole: str | None = None,
) -> str:
    """The one folded letter a single-letter parameter denotes.

    Refused when the fold yields more than one letter, because these callers
    compare letter against letter and a two-letter `expected` against a
    one-character `got` is not a comparison the violation can report honestly.
    The message names `fold_diacritics: false` because that genuinely works —
    the old `degenerate_output`/`allow_identity` advice named neither the cause
    nor a remedy (ADR 0035, D4).

    `whole` is for a caller mapping this over the characters of a longer
    parameter: `bivocalic`'s `vowels="ße"` is two letters, and reporting only
    `vowels='ß'` named the offending character while misquoting what the
    caller passed. Given it, the message carries both.
    """
    folded = fold_letter(value, pack, fold=fold)
    if len(folded) != 1:
        named = f"{field}={value!r}" if whole is None else f"{field}={whole!r}: {value!r}"
        raise InvalidParams(
            procedure_id,
            f"{named} folds to {folded!r} under fold_diacritics; "
            f"pass fold_diacritics=false to use it as a single letter",
        )
    return folded


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


#: Sentence punctuation a line may end on. Apostrophes and hyphens are absent by
#: design: French elision is part of the word (`l'âme`, `i'oy`), not decoration.
_TERMINAL_PUNCTUATION = '.,;:!?\u2026\u00b7\u00bb\u00ab"\u201c\u201d'


def line_identity(line: str) -> str:
    """The line as a repeated line, for asking whether two lines are the same one.

    A refrain returns carrying whatever punctuation its new syntax wants, and that
    is the form working rather than failing: Passerat's villanelle (1606) closes
    its refrain `Tourterelle:`, then `Tourterelle.`, then `Tourterelle,`, and
    Ranchin's triolet returns `du mois de mai` once bare and once as `de mai !`.
    Comparing raw lines read four canonical fixed-form texts as broken refrains.

    Only the end of the line is variable, so only the end is stripped. Apostrophes
    and internal punctuation stay: in French they carry an elision that is part of
    the word, and folding them would compare something other than the line.
    """
    return line.strip().rstrip(_TERMINAL_PUNCTUATION).strip().casefold()


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


#: A straight apostrophe and its typographic cousin. French elides a proclitic
#: onto the following word with either.
_ELISION_MARKS = ("'", "\u2019")


def split_elision(word: str) -> tuple[str, str]:
    """(proclitic-with-apostrophe or `""`, the rest).

    The tokeniser keeps an apostrophe-bearing token whole -- `l'île`,
    `d'espoir` -- because 94 real French words carry an internal apostrophe
    of their own (`aujourd'hui`), and splitting every apostrophe
    unconditionally would misread those (`denckring_fr_data._table_entry`
    tries the whole form against its table first, for exactly that reason,
    before falling back the same way this function always does).

    Two callers rely on the stronger fact that makes always-splitting safe
    for THEM specifically, each checked against its own table: `n_plus_7`'s
    noun list carries no apostrophe-bearing entry at all, so an apostrophe in
    a word handed to `noun_index` is always an elision boundary; `identical_rhyme`
    (`core/prosody.py`) only ever compares the segment split here against
    another segment split the same way, so a genuine apostrophe-word
    compared with itself still comes out identical. Neither caller needs the
    try-whole-first step `_table_entry` needs, because neither is looking a
    word up in a table that itself holds apostrophe-bearing entries.

    Splits at the LAST mark, the same as `_table_entry`, for a chained
    elision. Language-blind: no English or German word carries an
    apostrophe, so this is a silent no-op there.
    """
    for mark in _ELISION_MARKS:
        if mark in word:
            prefix, _, tail = word.rpartition(mark)
            return prefix + mark, tail
    return "", word
