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
#: dictionary, the WordNet glosses and the German lexicon, 21 MB of data the core
#: package never reads and ships no licence expression for.
#:
#: Raised from 1,000,000 on 2026-08-31, by decision, after chapter 4 tranche B crossed it
#: for real at 1,000,590 bytes on a clean checkout. Prose is what pushes this number:
#: `uv.lock`, the catalogue and four planning documents are the six largest members and
#: none of them is data.
#:
#: **This bound no longer catches the file it was set to catch, and that is a decision
#: waiting on the maintainer rather than an oversight.** Excluding `docs/superpowers/`
#: and `docs/seed/` on 2026-09-04 — they were always in `WORKING_DOCUMENTS` and always
#: refused by the docs site, and only the sdist's separate list disagreed — took a clean
#: checkout from 1,045,247 bytes (2026-09-02) to **759,242** (2026-09-04), both measured
#: in a detached worktree, because a build from the working tree swallows the untracked
#: `undefined/queneau-seams.png` and `CLAUDE.md` and reads about 82,000 higher.
#:
#: Removing ~360,000 bytes of prose does to this test's *purpose* exactly what raising
#: the number by 360,000 would have done. The smallest file it exists to catch is
#: `graded_words.txt.gz` at 249,917 bytes; re-included under `src/` it would now land the
#: archive near 1,009,000, which passes. The bound is presently decorative.
#:
#: Restoring it means lowering the number into the window `(841,816, 1,009,159)` — above
#: the working-tree build so a local run stays green, below the figure a re-included data
#: file would reach. **950,000 is the recommended value**: ~108,000 of headroom over a
#: working-tree build and ~191,000 over a clean one, while still failing on the data file.
#: 1,200,000 was raised by the maintainer's decision on 2026-08-31 and is left to the
#: maintainer to lower.
#:
#: The two halves of the trade still move against each other — every chapter of prose
#: shrinks the headroom and grows the archive — and there is still no per-file bound that
#: separates them: the largest legitimate member, `uv.lock`, is 330,512 bytes, larger than
#: the smallest data file. Whoever sets this next should set it knowing which half they
#: are spending.
MAX_SDIST_BYTES = 1_200_000


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


def test_the_sdist_does_not_carry_the_working_documents(sdist: Path) -> None:
    """`docs/expansion_ideas/` holds proposals, handovers and research notes addressed to
    whoever picks the work up — not documentation of what this package does, and nothing
    downstream reads them. Named here rather than left to the size bound alone, because
    the size bound has just been raised and a silent re-inclusion would now fit under it.
    They stay in git: ADRs 0030 and 0031 cite them.

    Read from `test_published_docs.WORKING_DOCUMENTS` rather than restated here.
    That list has always been right and the sdist's was not: `superpowers/` and
    `seed/` were kept off the docs site from the start and shipped to PyPI anyway,
    which nothing caught, because the two lists were maintained separately and
    the omission cost nothing until a spec pushed the archive past the size bound.
    One list, two consumers.
    """
    from test_published_docs import WORKING_DOCUMENTS

    stowaways = [
        name
        for name in _members(sdist)
        if any(name.startswith(f"docs/{folder}") for folder in WORKING_DOCUMENTS)
    ]
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
