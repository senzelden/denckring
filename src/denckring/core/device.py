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
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from denckring.core.errors import UnknownDevice

DEVICE_DIR = Path(str(files("denckring") / "data" / "devices"))


class Slot(BaseModel):
    """One ring, or one interchangeable position."""

    name: str
    alternatives: list[str]
    optional: bool = False

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
        """How many readings the device admits, counting a skip as an option."""
        total = 1
        for slot in self.slots:
            total *= len(slot.alternatives) + (1 if slot.optional else 0)
        return total


@lru_cache(maxsize=8)
def load(device_id: str) -> Device:
    """Read a device by id from the shipped data."""
    path = DEVICE_DIR / f"{device_id}.yaml"
    if not path.is_file():
        raise UnknownDevice(device_id, sorted(p.stem for p in DEVICE_DIR.glob("*.yaml")))
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Device.model_validate(raw)


def segment(text: str, device: Device) -> list[str] | None:
    """Cut `text` into one piece per slot, in order, or return None.

    Slots marked optional may contribute nothing. Returns the first reading
    found; a word the rings can spell in more than one way is still just
    producible, so the first is as good as any.
    """
    target = text.casefold()

    def walk(position: int, index: int) -> list[str] | None:
        if index == len(device.slots):
            return [] if position == len(target) else None
        slot = device.slots[index]
        # Longest alternatives first, so a greedy-looking reading is preferred
        # and the common case terminates sooner.
        for alternative in sorted(slot.alternatives, key=len, reverse=True):
            folded = alternative.casefold()
            if target.startswith(folded, position):
                rest = walk(position + len(folded), index + 1)
                if rest is not None:
                    return [alternative, *rest]
        if slot.optional:
            rest = walk(position, index + 1)
            if rest is not None:
                return ["", *rest]
        return None

    return walk(0, 0)


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
