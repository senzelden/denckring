"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

from dataclasses import dataclass

from denckring.core import device


@dataclass(frozen=True)
class Scene:
    """One recordable scene."""

    slug: str
    title: str
    procedure_id: str
    #: One line, shown under the stage and hidden by `?chrome=off`.
    caption: str


SCENES: list[Scene] = [
    Scene(
        slug="denckring",
        title="Der Denckring",
        procedure_id="denckring",
        caption="Harsdörffer, Nürnberg 1651. Turn the rings; read inward to outward.",
    ),
    Scene(
        slug="ideenwuerfeln",
        title="Ideenwürfeln",
        procedure_id="ideenwuerfeln",
        caption="Jean Paul's excerpt books: distant material forced together under one word.",
    ),
    Scene(
        slug="arca",
        title="Arca musarithmica",
        procedure_id="arca_musarithmica",
        caption="Kircher, 1650. The phrase is measured; the tablet for that length answers.",
    ),
    Scene(
        slug="n_plus_7",
        title="N+7",
        procedure_id="n_plus_7",
        caption="Lescure, 1961. Every noun, seven entries further down the dictionary.",
    ),
    Scene(
        slug="ghazal",
        title="Ghazal",
        procedure_id="ghazal",
        caption="Persian and Urdu: every couplet closes on the same word, rhyming before it.",
    ),
]


def scene(slug: str) -> Scene:
    """One scene by slug, or `KeyError`."""
    for candidate in SCENES:
        if candidate.slug == slug:
            return candidate
    raise KeyError(slug)


#: The figure the literature repeats for the Denckring. It is not a product of rings of
#: 12 and 120 at all — the catalogue row carries the arithmetic. The scene puts it next
#: to the real number rather than arguing in prose.
CLAIMED_COMBINATIONS = 97_209_600


@dataclass(frozen=True)
class RingSlot:
    """One disc, with everything written on it."""

    name: str
    alternatives: list[str]
    optional: bool


@dataclass(frozen=True)
class Rings:
    """The five discs, and the two counts."""

    slots: list[RingSlot]
    combinations: int
    claimed: int


def rings() -> Rings:
    """Harsdörffer's device as the shipped transcription has it."""
    loaded = device.load("harsdoerffer_1651")
    return Rings(
        slots=[
            RingSlot(name=slot.name, alternatives=list(slot.alternatives), optional=slot.optional)
            for slot in loaded.slots
        ],
        combinations=loaded.combinations,
        claimed=CLAIMED_COMBINATIONS,
    )


def pieces_for(word: str) -> list[str] | None:
    """The five ring pieces that spell `word`, one per slot, or `None` if the rings
    cannot spell it at all.

    The same segmentation `check` itself relies on — `denckring.core.device.segment`
    — so that when the library turns the rings for the scene (rather than a person
    clicking them), the diagram can be walked to the position that actually produced
    the word instead of leaving it wherever it happened to be. A skipped optional
    ring (prefix or suffix) comes back as `""`.
    """
    return device.segment(word, device.load("harsdoerffer_1651"))
