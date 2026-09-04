"""The seven-segment display, as a table and two functions.

Separate from the procedure because the explorer's stage scene needs the same
table, and a scene must not import a procedure's internals.

The table is a module constant rather than a pack capability, and that is a
decision (ADR 0037 D1). `prisoners_constraint` reads its forbidden set from the
pack's `letter_shapes` because ascenders and descenders genuinely differ by
orthography; seven-segment geometry does not — the display is the same machine
in Nuremberg, Boston and Lyon. `chronogram.VALUES` is the shape followed here.

Rotating a seven-segment glyph by 180 degrees swaps the segments a<->d, b<->e
and c<->f, and fixes g. Under that transform `2` maps onto itself and so shows
no letter at all, which is why the folk `2 -> Z` is refused (D2), and `6` and
`9` are each other's mirror and both land on G (D4).
"""

from __future__ import annotations

#: Digit -> the letter it shows when the machine is turned over. `6` and `9`
#: both give G: they are the rotation mirror of one another, and the display has
#: no case, so a word containing G has more than one digit spelling (ADR 0037 D4).
FROM_DIGIT = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "h",
    "5": "s",
    "6": "g",
    "7": "l",
    "8": "b",
    "9": "g",
}

#: Letter -> the digit this project emits for it. `g` resolves to `6` rather than
#: `9` because the practice's own name — *beghilos* — encodes g from 6. `check`
#: accepts either spelling; only the generator is bound by this direction.
TO_DIGIT = {
    "o": "0",
    "i": "1",
    "e": "3",
    "h": "4",
    "s": "5",
    "g": "6",
    "l": "7",
    "b": "8",
}

#: The eight letters a display can write, for a caller that wants the set rather
#: than the mapping. Named because `set(TO_DIGIT)` at a call site reads as if the
#: order might matter, and it does not.
ALPHABET = frozenset(TO_DIGIT)


def to_digits(word: str) -> str | None:
    """The digits that write `word`, or `None` where the display cannot.

    Reversed, because the machine is read upside down: the last letter is
    entered first. For a phrase this composes the same way — the digits of the
    *last* word are entered first — so a caller assembling one joins the words'
    digit strings in reverse order. Case is dropped; a display has none.
    """
    lowered = word.lower()
    if not lowered or any(ch not in TO_DIGIT for ch in lowered):
        return None
    return "".join(TO_DIGIT[ch] for ch in reversed(lowered))


def from_digits(digits: str) -> str:
    """The letters `digits` shows, reversed. A digit showing no letter is dropped.

    Dropping rather than raising keeps this total, so a caller can decode a
    partial entry — the stage scene decodes one keystroke at a time — without
    handling an exception per digit. Refusing a `2` is the procedure's own
    parameter validator's job, where the caller is naming a text and can be told
    that no text has that reading.
    """
    return "".join(FROM_DIGIT[ch] for ch in reversed(digits) if ch in FROM_DIGIT)
