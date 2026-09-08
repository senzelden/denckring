import re

import denckring

#: A version, not *the* version. Pinning the literal made this fail on the one
#: change that is always correct — the release bump — and it did, at 0.1.1.
#: That the number agrees with `pyproject.toml`, and with every sibling
#: distribution, is asserted properly by
#: `test_packaging.py::test_every_distribution_reports_the_same_version`.
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+].+)?$")


def test_version_is_exposed() -> None:
    assert SEMVER.match(denckring.__version__), denckring.__version__
