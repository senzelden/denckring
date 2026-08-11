"""Autodiscovery over `denckring.procedures`. No collector module, by design."""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any, TypeVar

from denckring.core.base import BaseProcedure
from denckring.core.errors import DuplicateProcedure, UnknownProcedure

_REGISTRY: dict[str, BaseProcedure[Any]] = {}
_DISCOVERED = False

C = TypeVar("C", bound=type[BaseProcedure[Any]])


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
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    package = importlib.import_module("denckring.procedures")
    for module in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"denckring.procedures.{module.name}")


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
