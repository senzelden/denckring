"""Autodiscovery over `denckring.procedures`. No collector module, by design."""

from __future__ import annotations

import importlib as importlib  # re-export: reaches `registry.importlib` (--no-implicit-reexport)
import pkgutil
import sys
import threading
from typing import Any, TypeVar

from denckring.core.base import BaseProcedure
from denckring.core.errors import DuplicateProcedure, UnknownProcedure

_REGISTRY: dict[str, BaseProcedure[Any]] = {}
_DISCOVERED = False
_LOCK = threading.RLock()

C = TypeVar("C", bound=type[BaseProcedure[Any]])


def _is_discovered() -> bool:
    """Read `_DISCOVERED` through a call, not a bare name.

    `_discover` checks this twice — once before the lock, once after — and a
    bare `if _DISCOVERED:` read twice in a row is, to mypy's single-threaded
    model, the same value both times, so the second check's `return` gets
    flagged `[unreachable]` under this project's `warn_unreachable`. It is
    reachable: another thread can set `_DISCOVERED` between the two reads.
    Routing the read through a function call mypy does not inline sidesteps
    the false positive without silencing real unreachable-code findings
    elsewhere with a blanket ignore.
    """
    return _DISCOVERED


def register(cls: C) -> C:
    """Instantiate and register a procedure class. Used as a decorator."""
    procedure_id = cls.id
    module_name = cls.__module__.rsplit(".", 1)[-1]
    if module_name != procedure_id:
        raise ValueError(
            f"Procedure id {procedure_id!r} must equal its module name, got {module_name!r}. "
            f"One module per procedure is enforced — see ADR 0007."
        )
    if procedure_id in _REGISTRY:
        raise DuplicateProcedure(procedure_id)
    _REGISTRY[procedure_id] = cls()
    return cls


def _discover() -> None:
    """Import every procedure module once, under a lock, rolling back on failure.

    `register` mutates `_REGISTRY` as a side effect of each import (the decorator
    above), so a failed import can leave some of this attempt's modules
    registered and others not. `_DISCOVERED` is set only after every module has
    imported without raising: a broken plugin does not poison the process for
    its whole lifetime, and a concurrent second caller blocks on `_LOCK` instead
    of reading a partially populated `_REGISTRY` (review finding P1-01).

    A retry after a rollback needs its modules to actually re-run: by ADR 0007
    a submodule's basename is its procedure id, so anything `pkgutil` lists
    that isn't already a `_REGISTRY` key is evicted from `sys.modules` first.
    Without that, `import_module` on an already-cached module is a no-op —
    it will not re-invoke `register` — so a module rolled back after a later
    module's import failure would stay permanently unregistered on retry,
    even though `_DISCOVERED` eventually goes True and the retry reports no
    error: `import_module` would keep returning its stale cached copy from
    before the rollback instead of re-running it.

    The eviction loop above also assumes every name `pkgutil` lists under
    `denckring.procedures` is a registering module — true today by ADR 0007,
    but unenforced here: a future shared helper module in this package would
    get evicted and re-imported on every retry, producing two module objects
    and breaking `isinstance` against any class it defines. It would not be
    registered, so it stays invisible to `all_procedures()` and to anything
    built on it (`docs/audit/`'s guard included) — the actual tripwire is
    `tests/test_registry.py::test_every_procedures_submodule_registers_a_procedure`,
    which walks `pkgutil.iter_modules` directly rather than going through the
    registry.
    """
    global _DISCOVERED
    if _is_discovered():
        return
    with _LOCK:
        if _is_discovered():
            return
        before = set(_REGISTRY)
        package = importlib.import_module("denckring.procedures")
        names = [module.name for module in pkgutil.iter_modules(package.__path__)]
        for name in names:
            if name not in before:
                sys.modules.pop(f"denckring.procedures.{name}", None)
        try:
            for name in names:
                importlib.import_module(f"denckring.procedures.{name}")
        except BaseException:
            for added in set(_REGISTRY) - before:
                del _REGISTRY[added]
            raise
        _DISCOVERED = True


def all_procedures() -> dict[str, BaseProcedure[Any]]:
    """Every registered procedure, by id."""
    _discover()
    return dict(_REGISTRY)


def get(procedure_id: str) -> BaseProcedure[Any]:
    """One registered procedure, or `UnknownProcedure`."""
    _discover()
    try:
        return _REGISTRY[procedure_id]
    except KeyError:
        raise UnknownProcedure(procedure_id) from None
