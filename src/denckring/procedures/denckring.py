"""Denckring — a word spelled by Harsdörffer's five rings."""

from __future__ import annotations

from pydantic import Field

from denckring.core import device as devices
from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams
from denckring.core.device import DeviceParams
from denckring.core.protocol import LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class DenckringParams(DeviceParams):
    require_all_rings: bool = Field(
        default=False,
        description="Every ring must contribute; skipping the prefix or suffix is not allowed.",
    )


class DenckringApplyParams(DenckringParams, SeedParams, ApplyParams):
    pass


@register
class Denckring(ConstructiveProcedure[DenckringParams, DenckringApplyParams]):
    """The device the package is named after.

    Five concentric discs of word parts; turning them lines up one part from
    each and spells a word. `check` asks whether a word could have come off the
    rings, which is a segmentation question and therefore decidable. `apply`
    turns them.

    Reading order is inward to outward, so a word is a prefix, an initial, a
    medial, a final and a suffix, with the prefix and suffix skippable — as they
    are on Harsdörffer's own rings, which carry a blank.
    """

    id = "denckring"

    #: The rings supply the word; `text` is never read. See
    #: `ConstructiveProcedure.ignores_input`.
    ignores_input = True

    @classmethod
    def params_model(cls) -> type[DenckringParams]:
        return DenckringParams

    def _check(self, text: str, pack: LanguagePack, params: DenckringParams) -> Report:
        machine = devices.load(params.device)
        words = word_spans(text, pack)
        violations: list[Violation] = []
        for offset, word in words:
            letters = "".join(ch for _, ch in letter_spans(word, pack, fold=False))
            reading = devices.segment(letters, machine)
            if reading is None:
                violations.append(
                    Violation(
                        rule="not_on_the_rings",
                        offset=offset,
                        found=word,
                        expected=f"a word the {machine.name} can spell",
                    )
                )
            elif params.require_all_rings and any(part == "" for part in reading):
                skipped = [
                    slot.name
                    for slot, part in zip(machine.slots, reading, strict=True)
                    if part == ""
                ]
                violations.append(
                    Violation(
                        rule="ring_skipped",
                        offset=offset,
                        found=word,
                        expected=(
                            f"a reading using every ring; {', '.join(skipped)} contributed nothing"
                        ),
                    )
                )
        return self._report(
            good=len(words) - len(violations),
            total=len(words),
            violations=violations,
            metrics={"words": float(len(words)), "combinations": float(machine.combinations)},
        )

    @classmethod
    def apply_params_model(cls) -> type[DenckringApplyParams]:
        return DenckringApplyParams

    def _produce(self, text: str, pack: LanguagePack, params: DenckringApplyParams) -> list[str]:
        """Turn the rings. `text` is ignored: the device supplies everything."""
        machine = devices.load(params.device)
        seed = params.seed
        while True:
            turned = devices.spin(machine, seed)
            word = "".join(turned)
            if word and (not params.require_all_rings or all(turned)):
                return [word]
            if seed is not None:
                # A fixed seed must stay deterministic, so nudge it rather than
                # spinning again on the same one.
                seed += 1
