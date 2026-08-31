"""Denckring — a word spelled by Harsdörffer's five rings."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from denckring.core import device as devices
from denckring.core.base import ApplyParams, ConstructiveProcedure, SeedParams, require_capability
from denckring.core.device import DeviceParams
from denckring.core.errors import InvalidParams
from denckring.core.protocol import Candidate, LanguagePack, Produced, Report, Violation
from denckring.core.registry import register
from denckring.core.text import letter_spans, word_spans


class DenckringParams(DeviceParams):
    require_all_rings: bool = Field(
        default=False,
        description="Every ring must contribute; skipping the prefix or suffix is not allowed.",
    )


class DenckringApplyParams(DenckringParams, SeedParams, ApplyParams):
    attestation: Literal["ignore", "mask"] = Field(
        default="ignore",
        description=(
            "Whether to read the device's validity mask: `mask` marks each spun "
            "word as attested or neglected and applies the mask's own policy."
        ),
    )


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

    def _produce(self, text: str, pack: LanguagePack, params: DenckringApplyParams) -> Produced:
        """Turn the rings `max_results` times. `text` is ignored: the device
        supplies everything.

        Several spins rather than one, because that is what makes the mask worth
        having: a device that flags which of its own outputs are real can only
        do so if it has produced more than one. `apply` still reads `texts[0]`,
        which under `attestation: mask` is an attested word when any of the spins
        found one.
        """
        machine = devices.load(params.device)
        mask = self._mask(machine, pack, params)
        words: dict[str, None] = {}
        seed = params.seed
        # Bounded rather than "until we have enough": every spin can come up
        # short (empty, or skipping a ring the caller required), and an
        # unbounded loop on a pathological device would not terminate.
        for _ in range(params.max_results * 8):
            if len(words) >= params.max_results:
                break
            turned = devices.spin(machine, seed)
            word = "".join(turned)
            if word and (not params.require_all_rings or all(turned)):
                words.setdefault(word)
            if seed is not None:
                # A fixed seed must stay deterministic, so nudge it rather than
                # spinning again on the same one.
                seed += 1
            elif not words:
                continue
        if mask is None:
            return Produced(candidates=[Candidate(text=word) for word in words])
        attested = {word: pack.is_word(word) for word in words}
        if mask.unmarked_policy == "drop":
            words = {word: None for word in words if attested[word]}
        return Produced(
            candidates=sorted(
                (
                    Candidate(text=word, metrics={"attested": float(attested[word])})
                    for word in words
                ),
                # Attested first, so `apply` hands back a real word when the rings
                # turned one up. Ties keep the order they were spun in, which is
                # what makes a fixed seed reproduce a fixed list.
                key=lambda candidate: -candidate.metrics["attested"],
            )
        )

    def _mask(
        self, machine: devices.Device, pack: LanguagePack, params: DenckringApplyParams
    ) -> devices.Mask | None:
        """The mask to apply, or None when the caller did not ask for one.

        Refuses rather than silently ignoring, in both directions: a device with
        no mask cannot answer the question, and a pack with no lexicon cannot
        either. `ignore` is the default so that a core-only install spins exactly
        as it always has and nothing acquires a data dependency by accident.
        """
        if params.attestation == "ignore":
            return None
        if machine.mask is None:
            raise InvalidParams(
                self.id, f"{machine.id} declares no validity mask, so there is nothing to read"
            )
        require_capability(pack, machine.mask.source, self.id)
        return machine.mask
