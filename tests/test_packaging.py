"""What the built distributions carry.

The pyproject is a claim about the artefacts; only building them settles it. A test
asserting that `pyproject.toml` contains an exclude pattern would pass while the build
ignored the pattern, so these tests build for real and read the result.
"""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: The core sdist carried both workspace members before this bound existed: the CMU
#: dictionary, the WordNet glosses and the German lexicon, 7.1 MB of data the core
#: package never reads and ships no licence expression for. It builds at 935,439 bytes
#: (0.94 MB) on a clean checkout now — 93.5% of this bound, largely from the docs this
#: chapter added (ADR 0029 and its specs); the next docs-heavy chapter could trip it.
MAX_SDIST_BYTES = 1_000_000


@pytest.fixture(scope="module")
def sdist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The core source distribution, built into a temporary directory."""
    if shutil.which("uv") is None:
        pytest.skip("uv is what builds the distributions")
    out = tmp_path_factory.mktemp("sdist")
    subprocess.run(
        ["uv", "build", "--sdist", "-o", str(out)], cwd=ROOT, check=True, capture_output=True
    )
    built = list(out.glob("denckring-*.tar.gz"))
    assert len(built) == 1, f"expected one sdist, got {built}"
    return built[0]


def _members(sdist: Path) -> list[str]:
    with tarfile.open(sdist) as archive:
        return [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]


def test_the_sdist_does_not_carry_the_workspace_members(sdist: Path) -> None:
    """`denckring-en-data` and `denckring-de-data` publish their own distributions under
    their own licence expressions — `Apache-2.0 AND CC-BY-4.0 AND BSD-2-Clause` and
    `Apache-2.0 AND CC0-1.0`. Shipping their data inside the core sdist duplicates
    several megabytes and puts third-party data under a declaration that does not
    describe it. The explorer is a development tool published nowhere."""
    stowaways = [name for name in _members(sdist) if name.startswith(("packages/", "apps/"))]
    assert stowaways == []


def test_the_sdist_keeps_what_a_packager_needs(sdist: Path) -> None:
    """Excluding is easy to overdo. A downstream packager building from source runs the
    suite, so `tests/` stays, and the catalogue is the package rather than an extra."""
    members = set(_members(sdist))
    for needed in (
        "src/denckring/data/catalogue.yaml",
        "tests/test_packaging.py",
        "pyproject.toml",
        "LICENSE",
        "NOTICE",
        "LICENSE-DATA",
    ):
        assert needed in members, f"the sdist dropped {needed}"


def test_the_sdist_stays_small(sdist: Path) -> None:
    """A size bound catches a re-inclusion the name-based tests above would miss —
    a data file added under `src/`, say, rather than under an excluded directory."""
    size = sdist.stat().st_size
    assert size < MAX_SDIST_BYTES, f"sdist is {size / 1_000_000:.1f} MB"
