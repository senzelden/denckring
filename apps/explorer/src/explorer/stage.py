"""The stage: what each scene is, and the data it needs.

Preparation only. Nothing here renders, and nothing here touches HTTP — a scene's
route reads from this module and hands the result to a template, so the thing a
scene claims can be tested without a browser.
"""

from __future__ import annotations

from dataclasses import dataclass


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
