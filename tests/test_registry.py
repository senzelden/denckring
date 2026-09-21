import pkgutil
import threading
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from pydantic import BaseModel

from denckring.core import catalogue, registry
from denckring.core.base import BaseProcedure
from denckring.core.errors import UnknownProcedure
from denckring.core.protocol import LanguagePack, Report


@pytest.fixture
def discovery_reset() -> Generator[dict[str, BaseProcedure[Any]], None, None]:
    """Reset `_REGISTRY`/`_DISCOVERED` to force `_discover()` to run again,
    and restore them unconditionally in a finalizer. Yields the pre-reset
    registry so the test can compare against its real size without having to
    capture it before the reset itself.

    Both concurrency tests below used to inline this same save/reset/restore,
    with the restore written as the last lines of the test body (a trailing
    `monkeypatch.setattr`, not a fixture). A failure anywhere earlier in the
    test — an assertion, an unexpected exception — skipped those trailing
    lines and left `_REGISTRY`/`_DISCOVERED` empty for every test that ran
    afterward in the same process. A `finally` runs even when the test body
    raises, so the module globals never come back wrong. This also
    de-duplicates the identical six lines both tests carried.
    """
    saved_registry = dict(registry._REGISTRY)
    saved_discovered = registry._DISCOVERED
    registry._REGISTRY = {}
    registry._DISCOVERED = False
    try:
        yield saved_registry
    finally:
        registry._REGISTRY = saved_registry
        registry._DISCOVERED = saved_discovered


class _LockProbe:
    """Wraps a real lock and fires an event the instant a caller starts
    contending for it — "about to block", not "some milliseconds have
    probably passed and it's probably blocked by now".

    `test_a_late_caller_blocks_until_discovery_finishes_rather_than_seeing_
    partial_state` used a fixed `time.sleep(0.1)` to give the first thread
    time to acquire `_LOCK` and reach the held import, then another
    `time.sleep(0.1)` before asserting the second thread had not finished —
    both are statements about the thread scheduler, not about the lock: on a
    loaded CI runner, 100ms is not a guarantee either thread has even been
    scheduled once, so the assertion can fail against perfectly correct code.
    Waiting on `contending` instead blocks the *test* thread until the
    *worker* thread has actually reached `with _LOCK:`, which is an exact
    synchronization point rather than a guess, and is what makes the
    `not second.done()` assertion that follows a statement about the lock.
    """

    def __init__(self, real_lock: threading.RLock) -> None:
        self._real_lock = real_lock
        self.contending = threading.Event()

    def __enter__(self) -> None:
        self.contending.set()
        self._real_lock.acquire()

    def __exit__(self, *exc_info: object) -> None:
        self._real_lock.release()


def test_get_raises_on_unknown_id() -> None:
    with pytest.raises(UnknownProcedure):
        registry.get("wobble")


def test_registered_ids_are_a_subset_of_the_catalogue() -> None:
    assert set(registry.all_procedures()) <= set(catalogue.ids())


def test_every_registered_procedure_is_a_base_procedure() -> None:
    for proc in registry.all_procedures().values():
        assert isinstance(proc, BaseProcedure)


def test_module_name_must_equal_procedure_id() -> None:
    for proc_id, proc in registry.all_procedures().items():
        assert type(proc).__module__.rsplit(".", 1)[-1] == proc_id


def test_every_procedures_submodule_registers_a_procedure() -> None:
    """`_discover`'s eviction/retry logic (see its docstring) assumes every
    name `pkgutil` lists under `denckring.procedures` is a registering module
    (ADR 0007) — nothing enforces that today. Issue #19 asked whether
    `tests/test_procedure_audit.py` would incidentally catch a shared helper
    module added there; verified empirically (a scratch non-registering
    module was added and both that guard and the full targeted suite still
    passed) that it does not: `all_procedures()` never sees an unregistered
    module, so it is invisible to a guard built on the registry. This test is
    the real tripwire that claim was reaching for."""
    package = registry.importlib.import_module("denckring.procedures")
    names = {module.name for module in pkgutil.iter_modules(package.__path__)}
    non_registering = sorted(names - set(registry.all_procedures()))
    assert not non_registering, (
        f"{non_registering} are modules under denckring.procedures that did not "
        f"register a procedure under their own name — a shared helper module "
        f"here would be silently evicted and re-imported by `_discover`'s retry "
        f"path, producing two module objects and breaking `isinstance` against "
        f"any class it defines (ADR 0007)"
    )


def test_registering_a_procedure_whose_module_disagrees_with_its_id_fails() -> None:
    class Params(BaseModel):
        pass

    class Mismatched(BaseProcedure[Params]):
        id = "definitely_not_this_module"

        @classmethod
        def params_model(cls) -> type[Params]:
            return Params

        def _check(self, text: str, pack: LanguagePack, params: Params) -> Report:
            raise NotImplementedError

    with pytest.raises(ValueError, match="module"):
        registry.register(Mismatched)


def test_a_late_caller_blocks_until_discovery_finishes_rather_than_seeing_partial_state(
    monkeypatch: pytest.MonkeyPatch, discovery_reset: dict[str, BaseProcedure[Any]]
) -> None:
    """P1-01: a second thread racing `_discover()` must block on the lock, not
    return a registry that is still being populated by the first thread."""
    saved_registry = discovery_reset

    probe = _LockProbe(registry._LOCK)
    monkeypatch.setattr(registry, "_LOCK", probe)

    release = threading.Event()
    original_import_module = registry.importlib.import_module

    def slow_import(name: str, *a: Any, **kw: Any) -> Any:
        result = original_import_module(name, *a, **kw)
        if name == "denckring.procedures.anagram":
            assert release.wait(timeout=5), "test setup did not release the held thread"
        return result

    monkeypatch.setattr(registry.importlib, "import_module", slow_import)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(registry.all_procedures)
        assert probe.contending.wait(timeout=5), "first thread never reached the lock"
        probe.contending.clear()
        second = pool.submit(registry.all_procedures)
        assert probe.contending.wait(timeout=5), "second thread never reached the lock"
        assert not second.done(), "a concurrent caller must block, not see a partial registry"
        release.set()
        result_first = first.result(timeout=5)
        result_second = second.result(timeout=5)

    assert result_first == result_second
    assert len(result_first) == len(saved_registry)


def test_a_failed_first_discovery_can_be_retried(
    monkeypatch: pytest.MonkeyPatch, discovery_reset: dict[str, BaseProcedure[Any]]
) -> None:
    """P1-01: a transient import failure must not permanently poison discovery,
    and must not leave the partially-registered ids of the failed attempt behind
    to collide as DuplicateProcedure on retry."""
    saved_registry = discovery_reset

    original_import_module = registry.importlib.import_module
    attempt = {"count": 0}

    def flaky_import(name: str, *a: Any, **kw: Any) -> Any:
        if name == "denckring.procedures.anagram" and attempt["count"] == 0:
            attempt["count"] += 1
            raise ImportError("simulated plugin failure")
        return original_import_module(name, *a, **kw)

    monkeypatch.setattr(registry.importlib, "import_module", flaky_import)

    with pytest.raises(ImportError):
        registry.all_procedures()
    assert registry._DISCOVERED is False, "a failed first load must not poison discovery"
    assert registry._REGISTRY == {}, "a failed attempt must roll back what it registered"

    result = registry.all_procedures()
    assert "anagram" in result
    assert len(result) == len(saved_registry)
