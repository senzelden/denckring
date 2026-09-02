"""What leaves this repository as documentation.

`release.yml` runs `mkdocs gh-deploy` on every `v*` tag, and mkdocs renders every file
under `docs/` whether or not the nav lists it — `not_in_nav` silences the warning and
publishes the page anyway. `exclude_docs` is the only thing that keeps a working
document off a public site. `scripts/build_docs.py` copies `CHANGELOG.md` in beside
them, so the changelog's structure is published too.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MKDOCS = ROOT / "mkdocs.yml"
CHANGELOG = ROOT / "CHANGELOG.md"

#: Directories under `docs/` addressed to whoever picks the work up rather than to a
#: reader of this package. `tests/test_packaging.py` keeps `docs/expansion_ideas/` out
#: of the sdist on exactly this reasoning, and the two exclusions have to agree: a
#: document not worth shipping is not worth publishing either.
WORKING_DOCUMENTS = ("superpowers/", "seed/", "audit/", "expansion_ideas/")


def test_the_site_excludes_every_working_document() -> None:
    excluded = set(yaml.safe_load(MKDOCS.read_text(encoding="utf-8"))["exclude_docs"].split())
    missing = [name for name in WORKING_DOCUMENTS if name not in excluded]
    assert not missing, f"mkdocs would publish {missing}"


def test_every_excluded_directory_still_exists() -> None:
    """An exclusion naming a directory that has since been renamed excludes nothing,
    and nothing else in the build would say so."""
    for name in WORKING_DOCUMENTS:
        assert (ROOT / "docs" / name).is_dir(), f"docs/{name} is named in an exclusion but gone"


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
