"""Poesie-Automat — a six-line poem the Landsberg flap-board could have shown."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from denckring.core import device as devices
from denckring.core.base import BaseProcedure
from denckring.core.device import Device, DeviceParams
from denckring.core.protocol import Lang, LanguagePack, Report, Violation
from denckring.core.registry import register
from denckring.core.text import line_spans

#: What stands between two modules on a line. The Denckring's rings concatenate
#: with nothing between them; this board's flaps carry whole words.
SEPARATOR = " "


def _reading(line: str, board: Device) -> list[str] | None:
    """The six flaps that spell `line`, or None. Whitespace runs are normalised."""
    return devices.segment(SEPARATOR.join(line.split()), board, separator=SEPARATOR)


def _first_module_that_fails(line: str, board: Device) -> int:
    """Which module the walk cannot get past, counting from zero.

    Every alternative is a whole number of space-separated words, so a module
    boundary always falls on a word boundary. That makes the question decidable
    by the same walk `_reading` uses: ask the first *k* modules to spell some
    word-prefix of the line, and take the smallest *k* for which none can. A
    second segmentation is not needed and would be a second thing to keep right.
    """
    words = line.split()
    for count in range(1, len(board.slots) + 1):
        prefix_board = board.model_copy(update={"slots": board.slots[:count]})
        reachable = any(
            devices.segment(SEPARATOR.join(words[:taken]), prefix_board, separator=SEPARATOR)
            is not None
            for taken in range(1, len(words) + 1)
        )
        if not reachable:
            return count - 1
    # `_first_module_that_fails` is only ever asked about a line `_reading`
    # already refused, so every module being reachable means the modules can
    # spell a prefix but not the whole line: the last one is where it ran out.
    return len(board.slots) - 1


class PoesieAutomatParams(DeviceParams):
    device: str = Field(
        default="poesieautomat_2000",
        description="Which device to read the modules from.",
    )


@register
class PoesieAutomat(BaseProcedure[PoesieAutomatParams]):
    """Enzensberger's flap-board: six lines, six modules each, ten flaps a module.

    `check` asks whether a six-line poem is one the board admits — each line cut
    into its six modules, each piece one of that module's ten alternatives. That
    is a segmentation question and therefore decidable, exactly as it is for the
    Denckring, and it is the same backtracking walk that answers it.

    `apply` presses the button.

    The board is data, and the data shipped here is not Enzensberger's. The
    schema is his and is what the checker checks; the 360 fillers were written
    for this project, because his are in copyright until 2092. The catalogue
    row says so, and so does the device file.

    Case is folded, as it is throughout `denckring.core.device`, so a poem typed
    without its capitals is still recognised as one the board can show.
    """

    id = "poesie_automat"

    @classmethod
    def params_model(cls) -> type[PoesieAutomatParams]:
        return PoesieAutomatParams

    def _check(self, text: str, pack: LanguagePack, params: PoesieAutomatParams) -> Report:
        machine = devices.load(params.device)
        expected = machine.lines
        found = line_spans(text)
        violations: list[Violation] = []
        good = 0
        for index, number in enumerate(expected):
            board = machine.for_line(number)
            if index >= len(found):
                violations.append(
                    Violation(
                        rule="missing_line",
                        offset=None,
                        found="",
                        expected=f"a line the {len(board.slots)} modules of line "
                        f"{number + 1} can spell",
                    )
                )
                continue
            offset, line = found[index]
            if _reading(line, board) is not None:
                good += 1
                continue
            position = _first_module_that_fails(line, board)
            slot = board.slots[position]
            violations.append(
                Violation(
                    rule="module_not_on_the_board",
                    offset=offset,
                    found=line.strip(),
                    expected=(
                        f"one of the {len(slot.alternatives)} alternatives for module "
                        f"{position + 1} ({slot.name}) of line {number + 1}"
                    ),
                )
            )
        for offset, line in found[len(expected) :]:
            violations.append(
                Violation(
                    rule="extra_line",
                    offset=offset,
                    found=line.strip(),
                    expected=f"a poem of {len(expected)} lines",
                )
            )
        total = max(len(expected), len(found))
        return self._report(
            good=good,
            total=total,
            violations=violations,
            metrics={
                "lines": float(len(expected)),
                "modules": float(len(machine.slots)),
                # The exact count is an int and stays one on the device;
                # `metrics` is float-valued, and 10^36 does not survive that
                # intact. `devices.load(...).combinations` is the honest figure.
                "combinations": float(machine.combinations),
            },
        )

    def apply(self, text: str, *, lang: Lang = "de", seed: int | None = None, **params: Any) -> str:
        """Press the button. `text` is ignored: the board supplies everything.

        The whole board is spun once and the flaps then grouped into lines —
        spinning each line separately under the same seed would draw the same
        sequence six times and stack six identical readings.
        """
        parsed = self.parse_params(params)
        machine = devices.load(parsed.device)
        turned = devices.spin(machine, seed)
        lines: dict[int, list[str]] = {number: [] for number in machine.lines}
        for slot, flap in zip(machine.slots, turned, strict=True):
            lines[slot.line].append(flap)
        return "\n".join(SEPARATOR.join(lines[number]) for number in machine.lines)
