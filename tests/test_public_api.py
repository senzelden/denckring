"""What a caller can import from `denckring` itself, without reaching into `core`.

The README puts everything under `denckring.core` outside the stability promise, so
any name a caller needs has to be importable from the top level. denckring-bench
imported four error classes, the golden-case harness and a private clause pattern
from `core`, because nothing else offered them (audit B2-B4, B7, B9).
"""

from __future__ import annotations

import inspect

import denckring
from denckring.core import errors


def test_every_error_class_is_exported_from_the_top_level() -> None:
    """Derived from the module, so a new error class is covered the day it lands."""
    defined = {
        name
        for name, value in vars(errors).items()
        if inspect.isclass(value)
        and issubclass(value, errors.DenckringError)
        and value.__module__ == errors.__name__
    }
    missing = sorted(
        name
        for name in defined
        if getattr(denckring, name, None) is not getattr(errors, name)
        or name not in denckring.__all__
    )
    assert missing == []
    assert "DenckringError" in defined


def test_the_pack_surface_is_exported_from_the_top_level() -> None:
    """`get_pack` and the protocol it returns are a contract (README, audit B3)."""
    from denckring import lang
    from denckring.core import protocol

    assert denckring.get_pack is lang.get_pack
    assert denckring.LanguagePack is protocol.LanguagePack
    assert denckring.PosTag is protocol.PosTag
    assert {"get_pack", "LanguagePack", "PosTag"} <= set(denckring.__all__)
    assert isinstance(denckring.get_pack("en"), denckring.LanguagePack)
