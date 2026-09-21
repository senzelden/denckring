from importlib.metadata import PackageNotFoundError

import pytest


def test_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """P3-02: an ad-hoc source-tree import should not raise just to read a
    version string that isn't needed to run anything.

    The restoring `importlib.reload(denckring)` used to be the last line of
    the test body, unguarded. If the *first* reload (the one that exercises
    the fallback) raised instead of falling back cleanly, the restoring
    reload never ran, and `monkeypatch`'s own teardown only undoes the
    `importlib.metadata.version` patch — not the reloaded module object,
    which `monkeypatch` never touched and has no way to know needs undoing.
    `denckring.__version__` would then stay `"0+unknown"` for every test that
    ran afterward in the same session. `try/finally` makes the restore
    unconditional instead."""
    from importlib.metadata import version as real_version

    def raise_not_found(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr("importlib.metadata.version", raise_not_found)
    import importlib

    import denckring

    try:
        reloaded = importlib.reload(denckring)
        assert reloaded.__version__ == "0+unknown"
    finally:
        monkeypatch.setattr("importlib.metadata.version", real_version)
        importlib.reload(denckring)  # restore the real installed version for later tests
