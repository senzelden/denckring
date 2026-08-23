"""The cartridge: an extra, caller-supplied search path for devices.

`denckring.core.device.load` reads `DENCKRING_DEVICE_PATH` — a colon-separated
list of directories searched before the packaged one — so a device's
word-lists no longer have to be ours. These tests are about that path and the
caching hazard it introduces, not about any one device's content; the
Denckring, Poesie-Automat and Llull suites already cover packaged devices in
depth and are untouched by this module.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from denckring import check
from denckring.core import device as devices
from denckring.core.device import DEVICE_PATH_ENV
from denckring.core.errors import UnknownDevice

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
    monkeypatch.setenv(DEVICE_PATH_ENV, f"{first_dir}:{second_dir}")
    assert devices.load("ordering").slots[0].alternatives == ["from-first"]
