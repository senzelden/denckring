"""P1-03: a pushed tag must match every workspace version and a stamped
changelog section before `release.yml` is allowed to build or publish."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from release_preflight import DISTRIBUTIONS, main

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_preflight.py"


def _run(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), tag],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )


def test_the_current_tag_and_version_agree() -> None:
    """A live guard: this fails the moment `pyproject.toml` and the changelog
    disagree with `v0.3.0`, which is what the CI job compares against the real
    pushed tag — this test compares against the workspace's own current state."""
    result = _run("v0.3.0")
    assert result.returncode == 0, result.stderr


def test_preflight_checks_every_distribution_the_packaging_suite_knows_about() -> None:
    """The two lists must be equal, not merely both present.

    `release_preflight.py` asked the reader to keep them in sync. On 2026-09-21
    the reader had not: `denckring_en_pos` was in the packaging list and missing
    here, so preflight would have cleared a release in which the seventh
    distribution carried a stale version — and preflight exists precisely because
    PyPI will not take a version back.

    Asserting equality rather than a count, so a distribution that is renamed or
    moved fails here too, and so the number never needs editing.
    """
    from test_packaging import DISTRIBUTIONS as PACKAGED

    assert set(DISTRIBUTIONS) == set(PACKAGED), (
        "release_preflight.DISTRIBUTIONS and test_packaging.DISTRIBUTIONS disagree; "
        f"only in preflight: {set(DISTRIBUTIONS) - set(PACKAGED)}; "
        f"only in packaging: {set(PACKAGED) - set(DISTRIBUTIONS)}"
    )


def test_a_mismatched_tag_is_refused() -> None:
    result = _run("v9.9.9")
    assert result.returncode != 0
    assert "9.9.9" in result.stderr


def test_an_unrecognised_tag_is_refused() -> None:
    """Was `test_a_tag_with_no_changelog_section_is_refused`: the name claimed
    this exercised the changelog check, but `v0.0.0-nonexistent` never gets
    that far — `tag_version` ("0.0.0-nonexistent") disagrees with the
    workspace version before `_changelog_has_section` is ever called, so this
    is really just another mismatched-tag case (verified by reading `main`:
    the version check runs, and returns, before the changelog check). The
    changelog branch is what `test_a_matching_tag_with_no_changelog_section_
    is_refused_by_that_check` below actually reaches and asserts on. Also
    dropped the unused `tmp_path` fixture and the `monkeypatch: object`
    parameter, which was never the real `pytest.MonkeyPatch` type and was
    never used either."""
    result = _run("v0.0.0-nonexistent")
    assert result.returncode != 0


def test_a_matching_tag_with_no_changelog_section_is_refused_by_that_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`test_a_tag_with_no_changelog_section_is_refused` above only proves a
    non-zero exit — its tag also fails the version-mismatch check first, so
    `_changelog_has_section` is never actually reached and could be hardcoded
    to always return `True` without any test noticing (P1-03 fix round 1).

    This builds an isolated fake workspace where every DISTRIBUTIONS
    `pyproject.toml` agrees with the tag, so the version check passes and the
    only possible failure is the changelog one — proven by asserting on the
    changelog message and the *absence* of the version-mismatch message,
    calling `main` directly (rather than via `_run`'s subprocess) with an
    injected `root` so no real file on disk needs editing."""
    version = "9.9.9"
    for _name, pyproject_path in DISTRIBUTIONS:
        target = tmp_path / pyproject_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'[project]\nversion = "{version}"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "## [Unreleased]\n\n## [9.9.8] - 2026-01-01\n", encoding="utf-8"
    )

    exit_code = main(f"v{version}", root=tmp_path)
    stderr = capsys.readouterr().err

    assert exit_code != 0
    assert "does not match workspace version" not in stderr
    assert f"CHANGELOG.md has no '## [{version}]' section" in stderr
