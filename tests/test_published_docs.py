"""What leaves this repository as documentation.

`release.yml` runs `mkdocs gh-deploy` on every `v*` tag, and mkdocs renders every file
under `docs/` whether or not the nav lists it — `not_in_nav` silences the warning and
publishes the page anyway. `exclude_docs` is the only thing that keeps a working
document off a public site. `scripts/build_docs.py` copies `CHANGELOG.md` in beside
them, so the changelog's structure is published too.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MKDOCS = ROOT / "mkdocs.yml"
CHANGELOG = ROOT / "CHANGELOG.md"

#: Directories under `docs/` addressed to whoever picks the work up rather than to a
#: reader of this package. `tests/test_packaging.py` keeps them out of the sdist on
#: exactly this reasoning, and the two exclusions have to agree: a document not worth
#: shipping is not worth publishing either.
#:
#: This was four entries until 2026-09-06, when `seed/` and `expansion_ideas/` were
#: removed from the repository and from all 552 commits of its history — an exclusion
#: naming them would guard a directory that cannot come back by accident.
#:
#: `superpowers/` went the same way and then came back as an *untracked* local scratch
#: area, so it is listed again. Untracked is not the same as absent: mkdocs publishes
#: what is under `docs/` and `uv build` archives what is in the working tree, and
#: neither consults git. A directory git cannot see still needs both exclusions.
#:
#: `stage_mockups/` joined them on 2026-09-07. It is tracked, and it had neither
#: exclusion — so it was bound for both the sdist and the public site while being
#: linked from nothing at all. That is the failure mode this list exists for and the
#: one nothing else catches: an unreferenced directory produces no dangling link, no
#: nav warning and no `--strict` failure. It is the rejected options behind the nine
#: machines on the stage; what was chosen is the app under `apps/`, which is not
#: documentation of this package either way.
#:
#: The list is split by a property rather than kept as one, because the check that an
#: exclusion still matches something can only be made against a directory that is in
#: the repository. Both halves are still excluded; `WORKING_DOCUMENTS` below is what
#: every other consumer reads, including `tests/test_packaging.py`.
TRACKED_WORKING_DOCUMENTS = ("audit/", "stage_mockups/")

#: Working documents that exist only in a maintainer's working tree. `superpowers/` was
#: removed from the repository and all 552 commits of its history on 2026-09-06 and then
#: recreated on disk as untracked local scratch, ignored via `.git/info/exclude`.
#:
#: It still needs both exclusions — mkdocs publishes what is under `docs/` and `uv build`
#: archives what is in the working tree, and neither consults git, so untracked is not
#: absent. But it is absent everywhere except that one machine, which is why it cannot
#: carry the existence check the tracked half does: `test_every_excluded_directory_still_exists`
#: asserted it on a fresh checkout and was red in CI from the day the entry was added
#: (2026-09-06) until this split, while passing locally the whole time. A guard that can
#: only pass on one machine states a fact about that machine, not a rule about the project.
LOCAL_ONLY_WORKING_DOCUMENTS = ("superpowers/",)

#: Everything kept off the site and out of the sdist, whatever git knows about it.
WORKING_DOCUMENTS = TRACKED_WORKING_DOCUMENTS + LOCAL_ONLY_WORKING_DOCUMENTS


def test_the_site_excludes_every_working_document() -> None:
    excluded = set(yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))["exclude_docs"].split())
    missing = [name for name in WORKING_DOCUMENTS if name not in excluded]
    assert not missing, f"mkdocs would publish {missing}"


def test_every_excluded_directory_still_exists() -> None:
    """An exclusion naming a directory that has since been renamed excludes nothing,
    and nothing else in the build would say so.

    Only the tracked half can be checked this way. The local-only half is verified by
    `test_the_local_only_exclusions_are_untracked` instead, which is the invariant that
    actually holds everywhere.
    """
    for name in TRACKED_WORKING_DOCUMENTS:
        assert (ROOT / "docs" / name).is_dir(), f"docs/{name} is named in an exclusion but gone"


def test_the_local_only_exclusions_are_untracked() -> None:
    """The split above is only honest while its two halves stay sorted, and the way it
    goes wrong is a local scratch directory being committed: the entry would then belong
    in `TRACKED_WORKING_DOCUMENTS`, where a rename is caught, and would sit unchecked in
    the local-only half instead. Asking git is what keeps the categorisation from drifting
    — and it is a question CI can answer, unlike whether the directory happens to be on
    the machine running the suite.
    """
    if shutil.which("git") is None:
        pytest.skip("git is what says whether a directory is tracked")
    for name in LOCAL_ONLY_WORKING_DOCUMENTS:
        tracked = subprocess.run(
            ["git", "ls-files", f"docs/{name}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert not tracked.strip(), (
            f"docs/{name} is tracked now, so it belongs in TRACKED_WORKING_DOCUMENTS "
            f"where a rename would be caught"
        )


def test_a_release_names_each_change_type_once() -> None:
    """`[Unreleased]` carried two `### Fixed` sections, because a chapter's block was
    appended to the end of the file rather than to the section it belonged in. The
    second list reads as the release's fixes and the first disappears above a hundred
    lines of `### Changed`. Keep a Changelog, which this file says it follows, names
    each type once per release.
    """
    release = ""
    seen: dict[str, list[str]] = {}
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            release = line[3:].strip()
            seen[release] = []
        elif line.startswith("### "):
            seen[release].append(line[4:].strip())
    for name, types in seen.items():
        duplicates = {t for t in types if types.count(t) > 1}
        assert not duplicates, f"{name} names {sorted(duplicates)} more than once"


def test_the_generated_index_carries_no_link_into_docs() -> None:
    """A root document points *into* `docs/`; once it is inside `docs/`, that
    prefix is one level too many and `mkdocs --strict` aborts on the dangling
    link. `build_docs.py` strips it, and this is what notices if it stops.

    Worth a test of its own because the failure is invisible locally. The gate
    in CLAUDE.md runs `mkdocs build --strict` but not `scripts/build_docs.py`
    before it, so a stale `docs/index.md` — the file is gitignored and generated
    — is what gets checked. The README gained an image link on 2026-09-04, four
    local `--strict` runs passed against an index generated before it, and CI
    caught it on the first push because CI regenerates first.
    """
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_docs.py")],
        check=True,
        capture_output=True,
        cwd=ROOT,
    )
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    assert "](docs/" not in index, "a link into docs/ survived generation"


def test_every_adr_is_in_the_nav() -> None:
    """`not_in_nav` silences the warning for the gallery; the ADRs are listed
    one by one on purpose, so a new record that nobody adds is a page the site
    publishes and no reader can reach."""
    nav = MKDOCS.read_text(encoding="utf-8")
    for adr in sorted((ROOT / "docs" / "adr").glob("[0-9]*.md")):
        assert f"adr/{adr.name}" in nav, f"{adr.name} is not in the nav"
