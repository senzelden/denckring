"""P2-05: none of the data-build scripts verified the SHA-256 of what they
downloaded, so a rebuild from repository state alone was not reproducible
and a mirror swap or network attacker could silently change shipped
linguistic data. `verify_or_record` is the one helper every download point
now calls.

Tested against the denckring-en-data copy specifically, not through a package
import: these packages depend on each other only as installed
distributions (denckring-de-frequency pins `denckring-de-data` by exact version),
never on one another's `scripts/` directories, so the helper is duplicated
rather than shared — see `packages/denckring-en-data/scripts/
_download_integrity.py`'s own docstring. `sys.path.insert` matches this
suite's own convention for reaching into a package's `scripts/` directory
(`test_de_frequency_build.py`), and this file lives in `tests/` rather than
inside the package because `testpaths = ["tests"]` is what the root gate and
CI's `test`/`coverage` jobs actually collect — a test placed in a package's
own `tests/` directory instead would never run in CI at all.

Only this one copy is ever imported and type-checked (`mypy_path` lists only
this package's `scripts/`), so nothing previously noticed if any of the
others drifted from it — and these files verify download integrity, so
silent drift between copies is worse than average.
`test_every_copy_of_download_integrity_hashes_identically` below closes that
gap, deriving the set of copies from the filesystem rather than a hardcoded
count: as of 2026-09-21 there are five (denckring-fr-data, denckring-en-data,
denckring-de-frequency, denckring-de-wiktionary and denckring-en-pos, per
`_download_integrity.py`'s own docstring), not the four issue #18 counted —
deriving the set from the filesystem is what stops that count needing to be
right, or edited again, the next time a distribution is added.
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "packages/denckring-en-data/scripts"))

from _download_integrity import verify_or_record


def test_a_matching_hash_is_accepted() -> None:
    data = b"hello"
    digest = verify_or_record(data, source="test", expected_sha256=None)
    assert verify_or_record(data, source="test", expected_sha256=digest) == digest


def test_a_mismatched_hash_exits_nonzero() -> None:
    import pytest

    with pytest.raises(SystemExit):
        verify_or_record(b"hello", source="test", expected_sha256="0" * 64)


def test_every_copy_of_download_integrity_hashes_identically() -> None:
    """Every `packages/*/scripts/_download_integrity.py` must be byte-identical
    to the one actually imported and tested above. The set of copies is
    derived from the filesystem, not written down as a count, so a new
    distribution that adds a sixth copy (or a seventh) needs no edit here —
    only for that copy to still match."""
    root = Path(__file__).resolve().parent.parent
    copies = sorted(root.glob("packages/*/scripts/_download_integrity.py"))
    assert len(copies) >= 2, (
        f"expected more than one copy to compare against, found {len(copies)}: {copies}"
    )
    digests = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in copies}
    assert len(set(digests.values())) == 1, (
        f"_download_integrity.py copies have drifted from each other: "
        f"{ {str(p): d for p, d in digests.items()} }"
    )
