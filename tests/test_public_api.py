"""What a caller can import from `denckring` itself, without reaching into `core`.

The README puts everything under `denckring.core` outside the stability promise, so
any name a caller needs has to be importable from the top level. denckring-bench
imported four error classes, the golden-case harness and a private clause pattern
from `core`, because nothing else offered them (audit B2-B4, B7, B9).
"""

from __future__ import annotations

import inspect

import pytest

import denckring
from denckring.core import errors
from denckring.core.registry import get
from denckring.eval.harness import golden_cases


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


def test_golden_cases_filters_by_language_and_keeps_the_whole_corpus_on_request() -> None:
    every = denckring.golden_cases(runnable=False)
    german = denckring.golden_cases("de", runnable=False)
    assert german and {case.lang for case in german} == {"de"}
    assert len(german) < len(every)
    assert {(case.procedure, case.name, case.lang) for case in every} == {
        (case.procedure, case.name, case.lang) for case in golden_cases()
    }


def test_golden_cases_drops_what_this_install_cannot_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pack lacking a capability drops every case whose row or whose own `requires`
    asks for it: run, each would end in `MissingCapability` or answer about the data.

    The Gryphius alexandrine is the case whose row needs only the heuristic and whose
    own verdict needs the dictionary, so it is the one dropped for the case alone."""

    class Heuristic:
        capabilities: frozenset[str] = frozenset({"tokens", "syllables.heuristic"})

    monkeypatch.setattr(denckring, "get_pack", lambda lang: Heuristic())
    kept = denckring.golden_cases()
    assert kept
    assert all(
        set(case.requires) | set(get(case.procedure).meta.requires) <= Heuristic.capabilities
        for case in kept
    )
    alexandrines = {case.name for case in kept if case.procedure == "alexandrine"}
    assert alexandrines
    assert "gryphius-traenen-alexandriner" not in alexandrines
