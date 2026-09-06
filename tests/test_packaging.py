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
#: **Lowered to 950,000 on 2026-09-06, by decision, because at 1,200,000 it no longer
#: caught the file it exists to catch.** Excluding `docs/superpowers/` and `docs/seed/`
#: on 2026-09-04 removed ~360,000 bytes of prose, which does to this test's *purpose*
#: exactly what raising the number by 360,000 would have done.
#:
#: Re-measured 2026-09-06, because the figures this comment carried had gone stale in
#: both directions and one of them was load-bearing:
#:
#:   - working tree, which swallows the untracked `undefined/queneau-seams.png`: 900,899
#:   - clean, the same build with that blob moved aside:                         838,734
#:   - the smallest file the bound exists to catch, `denckring-en-data`'s
#:     `graded_words.txt.gz`:                                                    249,917
#:
#: So the failure this guards against lands at **1,088,651** (clean + that file, by
#: arithmetic rather than measurement — the file is already gzipped, so a tar.gz cannot
#: compress it further). At 1,200,000 that passed, which is why the bound was decorative.
#:
#: The safe window is therefore `(900,899, 1,088,651)`: above a working-tree build so a
#: local run stays green, below the figure a re-included data file would reach. **950,000**
#: sits in it with ~49,000 of headroom locally and ~111,000 in CI, which never has the
#: untracked blob.
#:
#: Note the *smallest* data file sets the ceiling, not the largest. German's
#: `graded_words.txt.gz` is 433,830 and French's 413,181; either would be caught far more
#: easily. English is the binding constraint and the one to re-check if it ever shrinks.
#:
#: The two halves of the trade still move against each other — every chapter of prose
#: shrinks the headroom and grows the archive — and there is still no per-file bound that
#: separates them: the largest legitimate member, `uv.lock`, is 330,512 bytes, larger than
#: the smallest data file. Whoever sets this next should set it knowing which half they
#: are spending, and should re-measure rather than trust the numbers above.
MAX_SDIST_BYTES = 950_000


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


#: Every distribution in this workspace, as (import name, pyproject path). The six
#: publish from one workflow and must stay version-locked — `denckring-en-data`
#: subclasses the core English pack, `denckring-de-frequency` adds a capability to
#: the German one — so a version that drifts is a release that installs a pack
#: against a core it was not built for.
DISTRIBUTIONS = (
    ("denckring", "pyproject.toml"),
    ("denckring_en_data", "packages/denckring-en-data/pyproject.toml"),
    ("denckring_de_data", "packages/denckring-de-data/pyproject.toml"),
    ("denckring_de_wiktionary", "packages/denckring-de-wiktionary/pyproject.toml"),
    ("denckring_de_frequency", "packages/denckring-de-frequency/pyproject.toml"),
    ("denckring_fr_data", "packages/denckring-fr-data/pyproject.toml"),
)


def test_every_distribution_reports_the_same_version() -> None:
    """One version across the workspace, checked structurally rather than per package.

    Five separate assertions existed and only two were ever written, which is how
    `denckring-de-frequency` shipped with no `__version__` at all: nothing walked
    the list, so nothing noticed the sixth distribution was missing from it. That
    was the second time the sixth went uncounted — `release.yml` also said "five
    distributions" until 2026-09-06 — and the pattern is what this test is really
    for. Add a distribution to `DISTRIBUTIONS` and it is checked from then on.

    Both halves are held together: what the module reports at runtime, and what
    the packaging metadata claims. They are maintained by hand in two files and
    a release publishes the second while users import the first.
    """
    import tomllib
    from importlib import import_module

    root = Path(__file__).parent.parent
    seen: dict[str, str] = {}
    for module_name, pyproject in DISTRIBUTIONS:
        module = import_module(module_name)
        declared = getattr(module, "__version__", None)
        assert declared is not None, f"{module_name} exports no __version__"
        with (root / pyproject).open("rb") as handle:
            packaged = tomllib.load(handle)["project"]["version"]
        assert declared == packaged, f"{module_name}: {declared} but {pyproject} says {packaged}"
        seen[module_name] = declared

    assert len(set(seen.values())) == 1, f"versions have drifted apart: {seen}"
