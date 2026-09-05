"""The cartridge: an extra, caller-supplied search path for devices.

`denckring.core.device.load` reads `DENCKRING_DEVICE_PATH` — a colon-separated
list of directories searched before the packaged one — so a device's
word-lists no longer have to be ours. These tests are about that path and the
caching hazard it introduces, not about any one device's content; the
Denckring, Poesie-Automat and Llull suites already cover packaged devices in
depth and are untouched by this module.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from denckring import check
from denckring.core import device as devices
from denckring.core.device import DEVICE_PATH_ENV
from denckring.core.errors import MalformedDevice, MalformedFigure, UnknownDevice, UnknownFigure

TWO_SLOT_DEVICE = """\
id: {id}
name: A two-slot test device
source: tests/test_device.py, not a real device
slots:
  - name: first
    alternatives: ["ab", "xy"]
  - name: second
    alternatives: ["cd", "zz"]
"""


def _write(directory: Path, device_id: str, body: str | None = None) -> Path:
    path = directory / f"{device_id}.yaml"
    text = body if body is not None else TWO_SLOT_DEVICE.format(id=device_id)
    path.write_text(text, encoding="utf-8")
    return path


def test_unset_path_still_loads_a_packaged_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEVICE_PATH_ENV, raising=False)
    rings = devices.load("harsdoerffer_1651")
    assert rings.id == "harsdoerffer_1651"
    assert len(rings.slots) == 5


def test_a_device_found_only_on_the_extra_path_loads_and_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "cart_only")
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))

    machine = devices.load("cart_only")
    assert [slot.alternatives for slot in machine.slots] == [["ab", "xy"], ["cd", "zz"]]

    # Through the public API, not just through load: `check` is the library's
    # own way of asking whether a text is on a device, and the explorer must
    # not have to reimplement it for a device it did not ship.
    good = check("denckring", "abcd", lang="en", device="cart_only")
    assert good.satisfied

    bad = check("denckring", "nope", lang="en", device="cart_only")
    assert not bad.satisfied
    assert bad.violations[0].rule == "not_on_the_rings"


def test_a_device_on_the_extra_path_shadows_a_packaged_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "harsdoerffer_1651")
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))

    shadowed = devices.load("harsdoerffer_1651")
    # The extra path's two-slot device, not the packaged five-ring one.
    assert len(shadowed.slots) == 2


def test_unknown_device_lists_ids_from_the_extra_path_and_the_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "cart_visible")
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))

    with pytest.raises(UnknownDevice) as excinfo:
        devices.load("no_such_device_at_all")
    message = str(excinfo.value)
    assert "cart_visible" in message
    assert "harsdoerffer_1651" in message


def test_a_missing_directory_on_the_path_is_skipped_quietly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(DEVICE_PATH_ENV, "/no/such/directory/at/all")
    # A stale entry must not stop a packaged device from loading.
    rings = devices.load("harsdoerffer_1651")
    assert rings.id == "harsdoerffer_1651"


def test_changing_the_path_between_two_loads_of_the_same_id_is_not_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The caching hazard the brief calls out by name.

    `load` used to be `@lru_cache`d on `device_id` alone. If that cache had
    survived the refactor unchanged, the second `load` below would still
    return the first directory's device even though the environment now
    points somewhere else entirely — the id would resolve, silently, to a
    device that no longer exists on the path asked for.
    """
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    _write(first_dir, "swap", TWO_SLOT_DEVICE.format(id="swap"))
    # A distinct id in the second directory only — not a same-id, different
    # content version of "swap" — so a stale cache entry is caught by an
    # outright UnknownDevice rather than by comparing two device bodies.

    monkeypatch.setenv(DEVICE_PATH_ENV, str(first_dir))
    found = devices.load("swap")
    assert found.id == "swap"

    monkeypatch.setenv(DEVICE_PATH_ENV, str(second_dir))
    with pytest.raises(UnknownDevice):
        devices.load("swap")


def test_changing_the_path_can_also_change_what_the_same_id_resolves_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same hazard, the other way round: same id, different content."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    _write(first_dir, "swap2", TWO_SLOT_DEVICE.format(id="swap2"))
    _write(
        second_dir,
        "swap2",
        """\
id: swap2
name: A different two-slot test device
source: tests/test_device.py, not a real device
slots:
  - name: only
    alternatives: ["qq", "rr"]
""",
    )

    monkeypatch.setenv(DEVICE_PATH_ENV, str(first_dir))
    first = devices.load("swap2")
    assert len(first.slots) == 2

    monkeypatch.setenv(DEVICE_PATH_ENV, str(second_dir))
    second = devices.load("swap2")
    assert len(second.slots) == 1
    assert second.slots[0].alternatives == ["qq", "rr"]


def test_extra_directories_are_tried_in_path_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    _write(
        first_dir,
        "ordering",
        """\
id: ordering
name: From the first directory
source: tests/test_device.py
slots:
  - name: only
    alternatives: ["from-first"]
""",
    )
    _write(
        second_dir,
        "ordering",
        """\
id: ordering
name: From the second directory
source: tests/test_device.py
slots:
  - name: only
    alternatives: ["from-second"]
""",
    )
    # Joined with `os.pathsep` rather than a literal ":" — the separator this
    # variable is meant to use. A literal colon passes on POSIX and is the
    # reason this test could not see that the loader split on ":" as well.
    monkeypatch.setenv(DEVICE_PATH_ENV, os.pathsep.join([str(first_dir), str(second_dir)]))
    assert devices.load("ordering").slots[0].alternatives == ["from-first"]


# ── the id is untrusted input: absolute paths, `..`, separators, symlinks ──────

BROKEN_YAML = "id: [unclosed\n"

WRONG_SHAPE_YAML = """\
id: wrongshape
name: has a value the message must never echo
source: tests/test_device.py
slots: "not-a-list-of-slots-CANARY-VALUE"
"""

WRONG_SHAPE_FIGURE_YAML = """\
id: wrongshape
name: has a value the message must never echo
source: tests/test_device.py
letters: "not-a-list-of-letters-CANARY-VALUE"
levels: {}
"""


def test_an_absolute_device_id_does_not_escape_the_search_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Path.__truediv__` discards the left operand when the right is absolute.

    Without a guard, `directory / f"{device_id}.yaml"` for an absolute
    `device_id` is just `Path(device_id)` — the search directory is never
    consulted at all, and any file on the machine the process can read
    answers as though it were a device.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_SLOT_DEVICE.format(id="secret"))
    search_dir = tmp_path / "search"
    search_dir.mkdir()
    monkeypatch.setenv(DEVICE_PATH_ENV, str(search_dir))

    with pytest.raises(UnknownDevice):
        devices.load(str(outside / "secret"))


def test_a_traversal_device_id_does_not_escape_the_search_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`Path` never rejects a `..` segment; a bare-name check must."""
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_SLOT_DEVICE.format(id="secret"))
    search_dir = tmp_path / "search"
    search_dir.mkdir()
    monkeypatch.setenv(DEVICE_PATH_ENV, str(search_dir))

    with pytest.raises(UnknownDevice):
        devices.load(f"../{outside.name}/secret")


def test_a_separator_in_a_device_id_is_rejected_even_without_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `/` in the id is refused on its own, not only when it happens to traverse."""
    search_dir = tmp_path / "search"
    sub = search_dir / "sub"
    sub.mkdir(parents=True)
    _write(sub, "inner", TWO_SLOT_DEVICE.format(id="inner"))
    monkeypatch.setenv(DEVICE_PATH_ENV, str(search_dir))

    with pytest.raises(UnknownDevice):
        devices.load("sub/inner")


def test_a_symlinked_device_file_pointing_outside_its_directory_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A valid-looking id can still resolve outside the directory it is trusted in.

    The id pattern alone cannot catch this: `leaked` is a perfectly bare name.
    Only checking that the resolved file is actually inside the resolved search
    directory catches a symlink, placed in an otherwise-trusted directory, whose
    target is not.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_SLOT_DEVICE.format(id="secret"))
    search_dir = tmp_path / "search"
    search_dir.mkdir()
    (search_dir / "leaked.yaml").symlink_to(outside / "secret.yaml")
    monkeypatch.setenv(DEVICE_PATH_ENV, str(search_dir))

    with pytest.raises(UnknownDevice):
        devices.load("leaked")


def test_malformed_yaml_in_a_device_raises_a_denckring_error_without_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "broken", BROKEN_YAML)
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))

    with pytest.raises(MalformedDevice) as excinfo:
        devices.load("broken")
    message = str(excinfo.value)
    assert "unclosed" not in message


def test_valid_yaml_the_wrong_shape_raises_a_denckring_error_without_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "wrongshape", WRONG_SHAPE_YAML)
    monkeypatch.setenv(DEVICE_PATH_ENV, str(tmp_path))

    with pytest.raises(MalformedDevice) as excinfo:
        devices.load("wrongshape")
    exc = excinfo.value
    assert "CANARY-VALUE" not in str(exc)
    assert "CANARY-VALUE" not in str(exc.to_dict())


# ── the same three escapes and two malformed-content cases, for load_figure ────

TWO_LEVEL_FIGURE = """\
id: {id}
name: A test figure
source: tests/test_device.py, not a real figure
letters: ["A", "B"]
levels:
  absolute:
    A: "Alpha"
    B: "Beta"
"""


def test_an_absolute_figure_id_does_not_escape_figure_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_LEVEL_FIGURE.format(id="secret"))
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(UnknownFigure):
        devices.load_figure(str(outside / "secret"))


def test_a_traversal_figure_id_does_not_escape_figure_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_LEVEL_FIGURE.format(id="secret"))
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(UnknownFigure):
        devices.load_figure(f"../{outside.name}/secret")


def test_a_separator_in_a_figure_id_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figures_dir = tmp_path / "figures"
    sub = figures_dir / "sub"
    sub.mkdir(parents=True)
    _write(sub, "inner", TWO_LEVEL_FIGURE.format(id="inner"))
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(UnknownFigure):
        devices.load_figure("sub/inner")


def test_a_symlinked_figure_file_pointing_outside_figure_dir_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret", TWO_LEVEL_FIGURE.format(id="secret"))
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    (figures_dir / "leaked.yaml").symlink_to(outside / "secret.yaml")
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(UnknownFigure):
        devices.load_figure("leaked")


def test_malformed_yaml_in_a_figure_raises_a_denckring_error_without_the_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    _write(figures_dir, "broken", BROKEN_YAML)
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(MalformedFigure) as excinfo:
        devices.load_figure("broken")
    assert "unclosed" not in str(excinfo.value)


def test_valid_yaml_the_wrong_shape_raises_a_denckring_error_for_a_figure_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    _write(figures_dir, "wrongshape", WRONG_SHAPE_FIGURE_YAML)
    monkeypatch.setattr(devices, "FIGURE_DIR", figures_dir)

    with pytest.raises(MalformedFigure) as excinfo:
        devices.load_figure("wrongshape")
    exc = excinfo.value
    assert "CANARY-VALUE" not in str(exc)
    assert "CANARY-VALUE" not in str(exc.to_dict())


def test_the_search_path_splits_on_the_platform_separator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`DENCKRING_DEVICE_PATH` imitates `PATH` and must split the way `PATH`
    does: ";" on Windows, where ":" is the drive separator.

    It split on a literal ":" until 2026-09-05, so `C:\\Users\\...` tore into
    "C" and "\\Users\\...", neither entry was a directory, and every extra path
    was silently dropped — a documented feature that had never worked on
    Windows. Fifteen tests failed the first time CI ran on windows-latest, all
    from this one line.

    Simulated rather than skipped, so the regression is caught on any platform:
    patching `os.pathsep` is enough, because the split reads it at call time.
    """
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    for separator in (":", ";"):
        monkeypatch.setattr(os, "pathsep", separator)
        monkeypatch.setenv(DEVICE_PATH_ENV, separator.join([str(first), str(second)]))
        found = devices._device_search_path()
        assert first in found and second in found, separator
