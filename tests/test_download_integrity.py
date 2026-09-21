"""P2-05: none of the four data-build scripts verified the SHA-256 of what
they downloaded, so a rebuild from repository state alone was not
reproducible and a mirror swap or network attacker could silently change
shipped linguistic data. `verify_or_record` is the one helper all four
scripts' download points now call.

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
"""

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
