"""Combinatorial devices: ordered slots of alternatives.

Harsdörffer's five rings, Queneau's ten interchangeable sonnets and Kuhlmann's
Wechselsatz are one structure asked two different questions. The Denckring
*segments* a single word across its slots, because the parts concatenate with
nothing between them. The sonnet machines *select* one alternative per slot,
because the parts are already separated and the count is fixed.

Both are searches for some consistent reading, which is the shape metre, N+7 and
the free monosyllable already take.
"""

from __future__ import annotations

import random
from functools import lru_cache
from importlib.resources import files
from itertools import combinations
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from denckring.core.errors import UnknownDevice, UnknownFigure, UnknownLevel

DEVICE_DIR = Path(str(files("denckring") / "data" / "devices"))


class Slot(BaseModel):
    """One ring, or one interchangeable position.

    `line` groups slots that belong to the same line of a multi-line device. It
    defaults to 0, so a device whose YAML never mentions it — Harsdörffer's
    rings, which spell one word — reads as a single line and behaves exactly as
    before. A flap-board composing a six-line poem numbers its slots 0 to 5.
    """

    name: str
    alternatives: list[str]
    optional: bool = False
    line: int = 0

    def matches(self, piece: str) -> bool:
        folded = piece.casefold()
        return any(alternative.casefold() == folded for alternative in self.alternatives)


class Device(BaseModel):
    """An ordered set of slots, and where it comes from."""

    id: str
    name: str
    source: str
    slots: list[Slot]

    @property
    def combinations(self) -> int:
        """How many readings the device admits, counting a skip as an option.

        An `int`, never a float: a six-line board of six ten-way modules admits
        10^36 poems, which no float can hold exactly and Python's integers can.
        """
        total = 1
        for slot in self.slots:
            total *= len(slot.alternatives) + (1 if slot.optional else 0)
        return total

    @property
    def lines(self) -> list[int]:
        """The line numbers the slots carry, in order. `[0]` for a flat device."""
        return sorted({slot.line for slot in self.slots})

    def for_line(self, line: int) -> Device:
        """The slots of one line, as a device in their own right.

        Returning a `Device` rather than a bare list is what lets `segment`,
        `select`, `spin` and `combinations` be asked about one line without any
        of them learning what a line is.
        """
        return Device(
            id=f"{self.id}#{line}",
            name=f"{self.name}, line {line}",
            source=self.source,
            slots=[slot for slot in self.slots if slot.line == line],
        )


@lru_cache(maxsize=8)
def load(device_id: str) -> Device:
    """Read a device by id from the shipped data."""
    path = DEVICE_DIR / f"{device_id}.yaml"
    if not path.is_file():
        raise UnknownDevice(device_id, sorted(p.stem for p in DEVICE_DIR.glob("*.yaml")))
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Device.model_validate(raw)


def segment(text: str, device: Device, *, separator: str = "") -> list[str] | None:
    """Cut `text` into one piece per slot, in order, or return None.

    Slots marked optional may contribute nothing. Returns the first reading
    found; a word the rings can spell in more than one way is still just
    producible, so the first is as good as any.

    `separator` is what stands between two neighbouring pieces. It defaults to
    the empty string, which is Harsdörffer's rings: the parts concatenate with
    nothing between them. A board whose flaps carry whole words sets it to a
    space, and the same backtracking walk then splits a line into modules.

    A separator is expected before a piece only if some earlier slot actually
    contributed one, so a skipped optional slot leaves no orphaned separator
    behind — that is what `emitted` tracks. No device this package ships
    reaches that bookkeeping: the rings have optional slots and no separator,
    the flap-board has a separator and no optional slots. It is exercised by a
    synthetic device in `tests/test_poesie_automat.py` rather than by any
    shipped data, because a branch defended in prose and reached by nothing is
    a branch nobody has checked.
    """
    target = text.casefold()
    joint = separator.casefold()

    def walk(position: int, index: int, emitted: bool) -> list[str] | None:
        if index == len(device.slots):
            return [] if position == len(target) else None
        slot = device.slots[index]
        start: int | None = position
        if emitted and joint:
            start = position + len(joint) if target.startswith(joint, position) else None
        if start is not None:
            # Longest alternatives first, so a greedy-looking reading is preferred
            # and the common case terminates sooner.
            for alternative in sorted(slot.alternatives, key=len, reverse=True):
                folded = alternative.casefold()
                if target.startswith(folded, start):
                    rest = walk(start + len(folded), index + 1, True)
                    if rest is not None:
                        return [alternative, *rest]
        if slot.optional:
            rest = walk(position, index + 1, emitted)
            if rest is not None:
                return ["", *rest]
        return None

    return walk(0, 0, False)


def select(pieces: list[str], device: Device) -> list[bool]:
    """Which pieces sit on their corresponding slot.

    A piece per slot, in order. A shorter or longer text is reported by the
    caller rather than silently truncated here.
    """
    return [slot.matches(piece) for slot, piece in zip(device.slots, pieces, strict=False)]


def spin(device: Device, seed: int | None = None) -> list[str]:
    """Turn every ring at random. Deterministic under a fixed seed."""
    chooser = random.Random(seed)
    turned: list[str] = []
    for slot in device.slots:
        options = [*slot.alternatives, *([""] if slot.optional else [])]
        turned.append(chooser.choice(options))
    return turned


class DeviceParams(BaseModel):
    """Mixed into procedures driven by a combinatorial device."""

    device: str = Field(
        default="harsdoerffer_1651",
        description="Which device to read the slots from.",
    )


FIGURE_DIR = Path(str(files("denckring") / "data" / "figures"))


class Figure(BaseModel):
    """An alphabet read at several levels at once.

    Llull's ternary Ars letters nine principles B to K — J is not used — and the
    same letter names a dignity, a relation, a question, a subject, a virtue or a
    vice depending on the table it is read against. Turning the concentric wheels
    produces chambers of letters; what a chamber *says* depends on the level.

    Unlike a `Device`, whose slots are different sets, a figure draws every
    position from one alphabet, and a chamber is a combination rather than a
    product.
    """

    id: str
    name: str
    source: str
    letters: list[str]
    levels: dict[str, dict[str, str]]

    def level_names(self) -> list[str]:
        return sorted(self.levels)

    def read(self, chamber: str, level: str = "absolute") -> list[str]:
        """Spell a chamber out at one level, or raise if the level is unknown."""
        if level not in self.levels:
            raise UnknownLevel(self.id, level, self.level_names())
        table = self.levels[level]
        return [table[letter] for letter in chamber if letter in table]

    def chambers(self, arity: int = 3) -> list[str]:
        """Every combination of `arity` distinct letters, in alphabet order.

        Computed, never quoted: the count of the printed tabula has not been
        checked against a facsimile, and a figure derived from the letters is
        worth more than one taken from the literature.
        """
        return ["".join(combo) for combo in combinations(self.letters, arity)]


@lru_cache(maxsize=8)
def load_figure(figure_id: str) -> Figure:
    """Read a figure by id from the shipped data."""
    path = FIGURE_DIR / f"{figure_id}.yaml"
    if not path.is_file():
        raise UnknownFigure(figure_id, sorted(p.stem for p in FIGURE_DIR.glob("*.yaml")))
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    # `label` sits alongside the letters in each level; it documents, it does not map.
    raw["levels"] = {
        name: {k: v for k, v in table.items() if k != "label"}
        for name, table in raw["levels"].items()
    }
    return Figure.model_validate(raw)
